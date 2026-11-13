import os
import threading
import weakref
from typing import Callable, List, Optional
import ai.functions as func
from ai.config import ProgramConfig, ProgramSetting
from ai.services.history_manager import HistoryManager
from ai.services.model_orchestrator import ModelOrchestrator
from ai.services.engine_manager import EngineManager
from ai.modules.server.exceptions import ModelBusyError, ModelLoadError, ModelNotFoundError
from ai.services.process_manager import ProcessManager


ON_BUSY_WAIT = "wait"    # queue the swap until the current work finishes
ON_BUSY_FAIL = "fail"    # refuse the swap (ModelBusyError)
ON_BUSY_FORCE = "force"  # cancel the current work, then swap: only on an explicit user request
ON_BUSY_POLICIES = (ON_BUSY_WAIT, ON_BUSY_FAIL, ON_BUSY_FORCE)


class ModelLease:
    """One use of the loaded model (a chat generation). ``release`` is idempotent."""

    def __init__(self, hub: "BrainHub"):
        self._hub = hub
        self._released = False

    def release(self) -> None:
        if not self._released:
            self._released = True
            self._hub._end_generation()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.release()


class BrainHub:
    """
    Manages the core AI brain functionality, including model orchestration,
    session history management, and state control.

    This class acts as the central hub, coordinating between the LLM models
    (via ModelOrchestrator) and the persistent memory storage (via HistoryManager).
    """
    def __init__(self, config: ProgramConfig):
        """
        Initializes the BrainHub with the provided program configuration.

        Args:
            config: The global configuration object for the program.
        """
        self.config = config
        self.orchestrator = ModelOrchestrator(config)
        self.history_file: str = ""
        self.current_model_id: Optional[str] = None
        # Serialises load/unload: a swap must not run while another request is swapping.
        self._lock = threading.RLock()
        # Signalled whenever the model stops being in use, so a waiting swap can proceed.
        self._idle = threading.Condition(self._lock)
        self._generations = 0           # chat generations holding a ModelLease
        self._agent_running = False     # a web agent run uses the model for its whole run
        self._swap_target: Optional[str] = None
        self._cancel_hooks: List[Callable[[], None]] = []
        self.history = self.new_history(None, "default", None)
        

    def new_history(self, session_title: Optional[str], session_id: str, session_folder: Optional[str]) -> dict:
        """
        Initializes a fresh history structure dictionary.

        Args:
            session_title: The title for the new session.
            session_id: The unique identifier for the session.
            session_folder: The folder path where the session should be stored.

        Returns:
            A dictionary representing the initial state of the session history.
        """
        return {
            "session_id": session_id,
            "session_folder": session_folder,
            "session_title": session_title,
            "messages": [],
            "last_updated": None,
        }

    def route_memory(self, session_filepath: str, session_title: Optional[str], session_id: str, session_folder: Optional[str]):
        """
        Instructs the History Manager to hot-swap the active JSON file.

        This method changes the active session context, loading data from the
        specified file path.

        Args:
            session_filepath: The full path to the JSON file representing the session.
            session_title: The title to assign to the session.
            session_id: The ID to assign to the session.
            session_folder: The folder path associated with the session.
        """
        self.history_file = session_filepath
        self.history = self.new_history(session_title, session_id, session_folder)
        self.load_history_from_json(session_filepath)

    def add_history_message(self, role: str, content: str, images: Optional[list] = None):
            """
            Convenience method to add messages to the history from the API endpoints.

            Updates the history in memory and immediately saves the updated state
            to the active JSON file.

            Args:
                role: The role of the message (e.g., 'user', 'assistant').
                content: The textual content of the message.
            """
            message = {"role": role, "content": content}
            if images:
                message["images"] = images
            self.history["messages"].append(message)
            self.history["last_updated"] = self.get_timestamp()
            self.save_history_to_json(self.history_file)


    def load_history_from_json(self, filepath: str):
        """
        Loads a specific JSON file into the current history state.

        Handles file existence checks, JSON decoding errors, and structural validation.

        Args:
            filepath: The path to the JSON file to load.
        """
        if os.path.exists(filepath):
            import json
            try:
                with open(filepath, "r") as f:
                    loaded_data = json.load(f)
                    
                    # Validate if loaded_data is a dictionary and has the 'messages' key
                    if isinstance(loaded_data, dict) and "messages" in loaded_data and isinstance(loaded_data["messages"], list):
                        self.history = loaded_data
                        func.debug(f"BrainHub: Memory loaded from {filepath}")
                    else:
                        func.log(
                            f"BrainHub: Invalid session file format at {filepath}. Starting fresh.",
                            level="WARN",
                        )
                        self.history["messages"] = [] # Clear messages
                        self.history["last_updated"] = None # Reset last updated timestamp
            except json.JSONDecodeError:
                func.error(f"BrainHub: Corrupted session file at {filepath}. Starting fresh.")
                self.history["messages"] = [] # Clear messages
                self.history["last_updated"] = None # Reset last updated timestamp
        else:
            # Normal for a new session.
            func.debug(f"BrainHub: No session found at {filepath}. Starting fresh.")
            self.history["messages"] = [] # Clear messages
            self.history["last_updated"] = None # Reset last updated timestamp

    def save_history_to_json(self, filepath: str):
        """
        Saves the current in-memory history state to the specified JSON file.

        Args:
            filepath: The path where the history should be saved.
        """
        import json

        with open(filepath, "w") as f:
            json.dump(self.history, f, indent=4)
        func.debug(f"BrainHub: Memory saved to {filepath}")

   

    def get_timestamp(self) -> str:
        """
        Generates a standardized ISO format timestamp string for history entries.

        Returns:
            A string representing the current time in ISO format.
        """
        from datetime import datetime

        return datetime.now().isoformat()

    @staticmethod
    def model_key(name: Optional[str]) -> str:
        """
        The single identity of a model on the server: its config path under the models folder,
        lowercased, without ``.json`` ("small", "agents/lite").
        """
        key = (name or "default").strip().replace("\\", "/").lower()
        if key.endswith(".json"):
            key = key[:-len(".json")]
        return key or "default"

    # --- usage tracking -------------------------------------------------------------------

    SWAP_WAIT_TIMEOUT = 300.0   # seconds a "wait" swap waits for the current work
    FORCE_STOP_TIMEOUT = 30.0   # seconds a "force" swap waits for cancelled work to stop

    @property
    def agent_running(self) -> bool:
        """True while a web agent run uses the model; chat requests are refused meanwhile."""
        return self._agent_running

    @agent_running.setter
    def agent_running(self, value: bool) -> None:
        with self._lock:
            self._agent_running = bool(value)
            self._idle.notify_all()
            self._publish_activity()

    @property
    def busy(self) -> bool:
        """True while any chat generation or agent run uses the loaded model."""
        return self._generations > 0 or self._agent_running

    def add_cancel_hook(self, hook: Callable[[], None]) -> None:
        """Registers a callable that cancels long-running work (an agent run) for a forced swap."""
        self._cancel_hooks.append(hook)

    def acquire(self, model_id: str, system_prompt: str, model_config_data: Optional[dict] = None,
                on_busy: str = ON_BUSY_WAIT) -> ModelLease:
        """
        Loads ``model_id`` (see get_brain) and takes a lease on it in one step, so no swap can
        slip in between. Release the lease when the generation ends.
        """
        with self._lock:
            self.get_brain(model_id, system_prompt, model_config_data, on_busy=on_busy)
            self._generations += 1
            self._publish_activity()
            return ModelLease(self)

    @staticmethod
    def release_with(owner, lease: ModelLease) -> None:
        """Releases ``lease`` when ``owner`` (e.g. a streaming generator that never ran) is collected."""
        weakref.finalize(owner, lease.release)

    def _end_generation(self) -> None:
        with self._lock:
            self._generations = max(0, self._generations - 1)
            self._idle.notify_all()
            self._publish_activity()

    def _describe_usage(self) -> str:
        parts = []
        if self._agent_running:
            parts.append("an agent run")
        if self._generations:
            parts.append(f"{self._generations} chat{'s' if self._generations > 1 else ''}")
        return " and ".join(parts) or "nothing"

    def _publish_activity(self) -> None:
        """Mirrors the hub state into the process registry (an agent run publishes its own lines)."""
        if self._agent_running:
            return
        if self.busy:
            text = f"busy: {self._describe_usage()}"
        else:
            text = f"idle ({self.current_model_id})" if self.current_model_id else "idle (no model)"
        if self._swap_target:
            text += f", swap to {self._swap_target} pending"
        ProcessManager.set_state("activity", text)

    def _wait_until_idle(self, key: str, on_busy: str) -> None:
        """
        Called with the lock held when ``key`` differs from the loaded model and it is in use.

        Raises:
            ModelBusyError: ``fail``, or the wait timed out.
        """
        current = self.current_model_id or "unknown"
        if on_busy not in ON_BUSY_POLICIES:
            raise ValueError(f"Unknown on_busy '{on_busy}'. Use one of: {', '.join(ON_BUSY_POLICIES)}.")
        if on_busy == ON_BUSY_FAIL:
            raise ModelBusyError(f"Model '{current}' is in use by {self._describe_usage()}; not swapping to '{key}'.")

        timeout = self.SWAP_WAIT_TIMEOUT
        if on_busy == ON_BUSY_FORCE:
            func.out(f"BrainHub: Forced swap {current} -> {key}: cancelling {self._describe_usage()}.", level="WARNING")
            for hook in self._cancel_hooks:
                try:
                    hook()
                except Exception as e:
                    func.error(f"BrainHub: cancel hook failed: {e}")
            stop_event = getattr(self.orchestrator.llm, "stop_generation_event", None)
            if stop_event is not None:
                stop_event.set()
            timeout = self.FORCE_STOP_TIMEOUT

        func.out(f"BrainHub: {current} is in use by {self._describe_usage()}; swap to {key} waits.")
        self._swap_target = key
        self._publish_activity()
        try:
            if not self._idle.wait_for(lambda: not self.busy, timeout=timeout):
                raise ModelBusyError(
                    f"Model '{current}' is still in use by {self._describe_usage()} after {int(timeout)}s; "
                    f"not swapping to '{key}'.")
        finally:
            self._swap_target = None
            self._idle.notify_all()  # requests queued behind the swap re-check once we release the lock
            self._publish_activity()

    def get_brain(self, model_id: str, system_prompt: str, model_config_data: Optional[dict] = None,
                  on_busy: str = ON_BUSY_WAIT):
        """
        Ensures the requested model is loaded and active for interaction.

        The new config is resolved before anything is unloaded, so a bad model name leaves the
        current model running. A different model is unloaded (freeing GPU memory) before the new
        one loads. If that load fails the hub is left empty, never half-loaded.

        A swap never interrupts work in progress unless asked: while the loaded model is in use
        (a chat generation or an agent run), ``on_busy`` decides — ``wait`` (queue the swap until
        it is free), ``fail`` (refuse) or ``force`` (cancel the work, then swap).

        Args:
            model_id: The model config key (e.g. "small", "agents/lite").
            system_prompt: The system-level instruction prompt for the model.
            model_config_data: Optional full model config sent by the client; its ``model_name``
                                becomes the model identity.
            on_busy: ``wait`` (default), ``fail`` or ``force``; see above.

        Returns:
            The active LLM object instance from the ModelOrchestrator.

        Raises:
            ModelNotFoundError: No config file exists for ``model_id``.
            ModelLoadError: The config exists but the engine failed to load it.
            ModelBusyError: The model is in use and ``on_busy`` refused or timed out waiting.
        """
        if model_config_data and "model_name" in model_config_data:
            model_id = model_config_data["model_name"]
        key = self.model_key(model_id)

        with self._lock:
            # A queued swap goes first: new work for the old model must not keep it busy forever.
            if self._swap_target and self._swap_target != key:
                self._idle.wait_for(lambda: self._swap_target is None, timeout=self.SWAP_WAIT_TIMEOUT)
            llm = self.orchestrator.llm
            if llm is not None and self.current_model_id == key:
                if getattr(llm, "system_prompt", None) != system_prompt:
                    func.debug(f"BrainHub: Updating system prompt for loaded model '{key}'.")
                    llm.system_prompt = system_prompt
                return llm

            config_data = model_config_data
            if config_data is None:
                # Try the name as sent first, so a config file with capitals is still found.
                path = (self.orchestrator.find_config_file(str(model_id or "").strip())
                        or self.orchestrator.find_config_file(key))
                if path is None:
                    raise ModelNotFoundError(
                        f"Model '{key}' not found. Available: {', '.join(self.list_available_models()) or 'none'}")
                try:
                    config_data = EngineManager.load_config(path)
                except Exception as e:
                    raise ModelLoadError(f"Invalid model config '{path}': {e}") from e

            if not self.is_loadable(config_data):
                # A Jarvis config is a client of this server: loading it would call itself.
                raise ModelLoadError(
                    f"Model '{key}' is a Jarvis client config; the server needs a local engine (e.g. gguf).")

            if llm is not None:
                if self.busy:
                    self._wait_until_idle(key, on_busy)
                    llm = self.orchestrator.llm
                    if llm is not None and self.current_model_id == key:
                        return llm  # another waiter already loaded it
                if llm is not None:
                    func.out(f"BrainHub: Swapping {self.current_model_id or 'unknown'} -> {key}")
                    self.unload_brain()

            try:
                self.orchestrator.load(
                    model_config_name=key,
                    system_prompt=system_prompt,
                    model_config_data=config_data,
                    raise_errors=True,
                )
            except Exception as e:
                self.orchestrator.llm = None
                self.current_model_id = None
                raise ModelLoadError(f"Failed to load model '{key}': {e}") from e

            self.current_model_id = key
            self._idle.notify_all()
            self._publish_activity()
            func.out(f"BrainHub: {key} is now HOT.")
            return self.orchestrator.llm

    def unload_brain(self):
        """
        Frees the active model. The hub state is cleared even if the engine's unload fails,
        so the next request always starts from a known empty state.

        Returns:
            The key of the model that was unloaded, or None when none was loaded.
        """
        with self._lock:
            llm = self.orchestrator.llm
            model_id = self.current_model_id
            self.orchestrator.llm = None
            self.orchestrator.active_model_name = ""
            self.current_model_id = None
            if llm is None:
                return None
            func.out(f"BrainHub: Unloading {model_id or 'unknown'}...")
            try:
                llm.unload()
            except Exception as e:
                func.error(f"BrainHub: Unload of {model_id or 'unknown'} failed: {e}")
            return model_id

    @staticmethod
    def is_loadable(config_data: dict) -> bool:
        """A server can load any engine except ``jarvis``, which is a client of this server."""
        return str(config_data.get("model_type", "")).lower() != "jarvis"

    @staticmethod
    def has_vision(config_data: dict) -> bool:
        """Whether a config's model can read images: Gemini, or GGUF with a vision projector."""
        model_type = str(config_data.get("model_type", "")).lower()
        properties = config_data.get("model_properties") or {}
        return model_type == "gemini" or (model_type == "gguf" and bool(properties.get("mmproj_filename")))

    def list_model_configs(self, folder: Optional[str] = None) -> list:
        """
        Every model config the server knows, subfolders included, loadable or not.

        Args:
            folder: Optional subfolder of the models folder ("chat"); only configs under it are
                    listed. Keys stay full paths ("chat/small"), so they can be sent as ``model``.

        Returns:
            Dicts sorted by key: ``key`` (what a request sends as ``model``), ``model_name``
            (display name), ``model_type``, ``vision`` (reads images) and ``loadable`` (False for ``jarvis`` client configs
            and for files that are not valid JSON, which also carry ``error``).
        """
        prefix = ""
        if folder:
            prefix = folder.strip().replace("\\", "/").strip("/").lower()
            prefix = f"{prefix}/" if prefix else ""
        configs = []
        for key, path in self.orchestrator.list_config_files().items():
            if prefix and not key.lower().startswith(prefix):
                continue
            entry = {"key": key.lower(), "model_name": key, "model_type": "", "loadable": False, "vision": False}
            try:
                data = EngineManager.load_config(path)
                entry["model_name"] = data.get("model_name") or key
                entry["model_type"] = str(data.get("model_type", ""))
                entry["loadable"] = self.is_loadable(data)
                entry["vision"] = self.has_vision(data)
            except Exception as e:
                entry["error"] = str(e)
            configs.append(entry)
        return configs

    def list_available_models(self) -> list:
        """
        The model keys a request may ask for: loadable configs only, subfolders included.

        Returns:
            Sorted model keys ("small", "agents/lite").
        """
        return [c["key"] for c in self.list_model_configs() if c["loadable"]]

    def get_stats(self) -> dict:
        """
        Extracts the 'fuel gauge' statistics from the active model.

        Returns:
            A dictionary containing usage metrics, or {"active": False} if no model is loaded.
        """
        if not self.orchestrator.llm:
            return {"active": False}

        stats = self.orchestrator.llm.token_info_count
        return {
            "active": True,
            "model": self.current_model_id,
            "prompt_tokens": stats.prompt_count,
            "total_tokens": stats.total_prompt_count,
            "output_tokens": stats.printed_tokens_count,
            "window": stats.max_context_window,
            "usage_percent": (
                round((stats.prompt_count / stats.max_context_window * 100), 2)
                if stats.max_context_window > 0
                else 0
            ),
        }