"""
What to do when a local model does not fit in the free GPU memory.

When a load fails with GpuMemoryError, GpuAdvisor tells the user who holds the GPU (other JARVIS
instances from the process registry, other programs from nvidia-smi) and offers what can be done:
use a running JARVIS server instead, ask it to switch model (when free, or now), or load the model
partly on the GPU. It never stops another program.
"""

import copy
import gc
import os
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Callable, List, Optional

import ai.functions as func
from ai.color import Color
from ai.core.llms.load_errors import GpuMemoryError
from ai.services.process_manager import ProcessManager


@dataclass
class GpuHolder:
    """A process using GPU memory; ``instance`` is its registry entry when it is a JARVIS instance."""
    pid: int
    name: str
    used_mb: int
    instance: Optional[dict] = None


@dataclass
class GpuSnapshot:
    free_mb: int
    total_mb: int
    holders: List[GpuHolder] = field(default_factory=list)


@dataclass
class Choice:
    label: str
    run: Callable[[], object]


def model_key(name: Optional[str]) -> str:
    """A model config's identity: its path under the models folder, lowercased, without .json."""
    key = (name or "default").strip().replace("\\", "/").lower()
    return (key[:-len(".json")] if key.endswith(".json") else key) or "default"


def nvidia_snapshot(timeout: float = 5.0) -> Optional[GpuSnapshot]:
    """Free/total memory of the first NVIDIA GPU and the processes using it; None without nvidia-smi."""
    def query(args):
        out = subprocess.run(["nvidia-smi", *args, "--format=csv,noheader,nounits"],
                             capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
        if out.returncode != 0:
            raise OSError(out.stderr.strip())
        return [line.split(",") for line in out.stdout.strip().splitlines() if line.strip()]

    try:
        free, total = (int(v.strip()) for v in query(["--query-gpu=memory.free,memory.total"])[0][:2])
        holders = []
        for row in query(["--query-compute-apps=pid,process_name,used_memory"]):
            try:
                holders.append(GpuHolder(int(row[0]), os.path.basename(row[1].strip()), int(row[2].strip())))
            except (ValueError, IndexError):
                continue
        return GpuSnapshot(free, total, holders)
    except (OSError, ValueError, IndexError, subprocess.SubprocessError):
        return None


def _gb(mb: int) -> str:
    return f"{mb / 1024:.1f} GB"


class GpuAdvisor:
    """Resolves a GpuMemoryError into a working model, or None when there is nothing to do."""

    PARTIAL_HEADROOM = 0.6  # share of the free memory given to layers (the rest: KV cache, buffers)

    def __init__(self, config_name: str, model_config: dict, system_prompt: str, tool_registry=None,
                 loader: Optional[Callable] = None, snapshot: Optional[Callable[[], Optional[GpuSnapshot]]] = None,
                 instances: Optional[Callable[[], List[dict]]] = None, interactive: Optional[bool] = None,
                 ask: Callable[[str], str] = input, find_config: Optional[Callable[[str], Optional[dict]]] = None):
        """
        Args:
            config_name: The model config that failed ("default", "agents/lite").
            model_config: Its loaded config dict.
            system_prompt, tool_registry: Passed on to whichever model gets loaded.
            loader: Builds a model from a config (default EngineManager.load_model_instance).
            snapshot: GPU state (default nvidia-smi).
            instances: Live JARVIS instances (default the process registry).
            interactive: Whether the user can answer (default: stdin and stdout are terminals).
            ask: Reads the user's answer.
            find_config: Loads another config by key, to tell when a server holds the same model.
        """
        self.config_name = config_name
        self.key = model_key(config_name)
        self.model_config = model_config
        self.system_prompt = system_prompt
        self.tool_registry = tool_registry
        if loader is None:
            from ai.services.engine_manager import EngineManager
            loader = EngineManager.load_model_instance
        self.loader = loader
        self.snapshot = snapshot or nvidia_snapshot
        self.instances = instances or self._registry_instances
        self.interactive = (sys.stdin.isatty() and sys.stdout.isatty()) if interactive is None else interactive
        self.ask = ask
        self.find_config = find_config or self._find_config

    # --- discovery -------------------------------------------------------------------------

    @staticmethod
    def _registry_instances() -> List[dict]:
        from ai.services.directory_manager import DirectoryManager
        return ProcessManager.list_instances(DirectoryManager().get_pid_directory())

    @staticmethod
    def _find_config(key: str) -> Optional[dict]:
        from ai.services.engine_manager import EngineManager
        from ai.services.model_orchestrator import ModelOrchestrator
        path = ModelOrchestrator.find_config_file(key)
        try:
            return EngineManager.load_config(path) if path else None
        except Exception:
            return None

    def _servers(self) -> List[dict]:
        me = str(os.getpid())
        return [i for i in self.instances()
                if i.get("mode") == "server" and i.get("endpoint") and i.get("pid") != me]

    def _same_model(self, server_key: str) -> bool:
        """The server's model is this one: same key, or a config for the same model file."""
        if not server_key:
            return False
        if model_key(server_key) == self.key:
            return True
        other = self.find_config(server_key) or {}
        mine, theirs = self.model_config.get("model_properties", {}), other.get("model_properties", {})
        return (other.get("model_type") == self.model_config.get("model_type")
                and bool(mine.get("gguf_filename")) and mine.get("gguf_filename") == theirs.get("gguf_filename")
                and mine.get("model_repo_id") == theirs.get("model_repo_id"))

    # --- actions ---------------------------------------------------------------------------

    def _via_server(self, server: dict, server_model: str, on_busy: Optional[str] = None):
        """A jarvis client model that sends this conversation to ``server``."""
        properties = copy.deepcopy(self.model_config.get("model_properties", {}))
        properties.update(base_url=server["endpoint"], server_model=server_model)
        if on_busy:
            properties["on_busy"] = on_busy
        config = {"model_name": self.model_config.get("model_name", self.key),
                  "model_type": "jarvis", "model_properties": properties}
        func.out(f"{Color.CYAN}[ * ] Using the JARVIS server at {server['endpoint']} ({server_model})."
                 f"{Color.RESET}")
        if on_busy == "wait" and not str(server.get("activity", "")).startswith("idle"):
            func.out(f"{Color.CYAN}      It switches to {server_model} once its current work ends.{Color.RESET}")
        return self.loader(model_config=config, system_prompt=self.system_prompt, tool_registry=self.tool_registry)

    def _layer_plan(self, error: GpuMemoryError, free_mb: Optional[int]) -> List[int]:
        """GPU layer counts to try, most first, ending with CPU only (0)."""
        blocks = self._block_count(error.model_path)
        if blocks and free_mb is not None and error.model_path and os.path.isfile(error.model_path):
            per_layer_mb = os.path.getsize(error.model_path) / (1024 * 1024) / blocks
            first = int(free_mb * self.PARTIAL_HEADROOM / per_layer_mb) if per_layer_mb > 0 else 0
            first = max(0, min(first, blocks - 1))
        else:
            first = (blocks or 32) // 2
        plan = [first, first // 2, 0]
        return sorted({n for n in plan if n >= 0}, reverse=True)

    @staticmethod
    def _block_count(model_path: str) -> Optional[int]:
        """Number of layers, from the GGUF metadata (reads the vocabulary only, no weights)."""
        if not model_path or not os.path.isfile(model_path):
            return None
        try:
            from llama_cpp import Llama
            meta = Llama(model_path=model_path, vocab_only=True, verbose=False).metadata or {}
            arch = meta.get("general.architecture", "")
            return int(meta[f"{arch}.block_count"])
        except Exception as e:
            func.debug(f"GpuAdvisor: cannot read the layer count of {model_path}: {e}")
            return None

    def _partial(self, error: GpuMemoryError, free_mb: Optional[int]):
        """Loads the model with fewer layers on the GPU, down to CPU only."""
        last = error
        func.out(f"{Color.CYAN}[ * ] Finding how much of {self.key} fits on the GPU...{Color.RESET}")
        for layers in self._layer_plan(error, free_mb):
            config = copy.deepcopy(self.model_config)
            properties = config.setdefault("model_properties", {})
            properties["n_gpu_layers"] = layers
            if layers == 0:
                # Really CPU only: with a CUDA build, llama.cpp still puts the KV cache and the
                # compute buffer (which grows with n_ctx) on the GPU at 0 layers.
                properties.update(offload_kqv=False, op_offload=False)
            try:
                llm = self.loader(model_config=config, system_prompt=self.system_prompt,
                                  tool_registry=self.tool_registry)
            except GpuMemoryError as e:
                func.debug(f"GpuAdvisor: {layers} GPU layers did not fit.")
                last = e.with_traceback(None)  # its frames hold the failed attempt alive
                del e
                gc.collect()
                continue
            where = f"with {layers} layers on the GPU and the rest on the CPU" if layers else "on the CPU only"
            func.out(f"{Color.YELLOW}[ * ] Loaded {self.key} {where}: answers will be slower.{Color.RESET}")
            return llm
        raise last

    # --- decision --------------------------------------------------------------------------

    def _describe(self, snapshot: Optional[GpuSnapshot], servers: List[dict]) -> List[str]:
        lines = [f"{Color.YELLOW}[ ! ] Not enough free GPU memory to load {self.key}"
                 + (f" ({_gb(snapshot.free_mb)} free of {_gb(snapshot.total_mb)})." if snapshot else ".")
                 + Color.RESET]
        by_pid = {i.get("pid"): i for i in self.instances()}
        holders = snapshot.holders if snapshot else []
        for holder in holders:
            holder.instance = by_pid.get(str(holder.pid))
        # Skip ourselves (our failed load left a CUDA context) and tiny users like the compositor.
        shown = [h for h in holders if h.used_mb >= 64 and h.pid != os.getpid()]
        if shown or servers:
            lines.append("      In use by:")
        for h in sorted(shown, key=lambda h: -h.used_mb):
            if h.instance:
                what = f"JARVIS {h.instance.get('mode', '?')}"
                if h.instance.get("model"):
                    what += f" ({h.instance['model']})"
                activity = f" - {h.instance['activity']}" if h.instance.get("activity") else ""
                lines.append(f"        • {what}  PID {h.pid}  {_gb(h.used_mb)}{activity}")
            else:
                lines.append(f"        • {h.name}  PID {h.pid}  {_gb(h.used_mb)}")
        listed = {str(h.pid) for h in shown}
        for s in servers:
            if s.get("pid") not in listed:
                lines.append(f"        • JARVIS server ({s.get('model') or 'no model'})  PID {s.get('pid')}"
                             f" - {s.get('activity', '')}")
        return lines

    def _choices(self, error: GpuMemoryError, snapshot: Optional[GpuSnapshot], servers: List[dict]) -> List[Choice]:
        choices = []
        free_mb = snapshot.free_mb if snapshot else None
        for s in servers:
            current = s.get("model", "")
            busy = not str(s.get("activity", "idle")).startswith("idle")
            if current and self._same_model(current):
                choices.append(Choice(f"Use the running server: it already has this model ({current})",
                                      lambda s=s, c=current: self._via_server(s, c)))
                continue
            if current:
                choices.append(Choice(f"Use the running server with its model ({current})",
                                      lambda s=s, c=current: self._via_server(s, c)))
            when = "when its current work ends" if busy else "now (it is idle)"
            choices.append(Choice(f"Ask the server to switch to {self.key} {when}",
                                  lambda s=s: self._via_server(s, self.key, on_busy="wait")))
            if busy:
                choices.append(Choice(f"Force the server to switch to {self.key} now (CANCELS its current work)",
                                      lambda s=s: self._via_server(s, self.key, on_busy="force")))
        choices.append(Choice("Load it here, partly on the GPU (slower)", lambda: self._partial(error, free_mb)))
        return choices

    def resolve(self, error: GpuMemoryError):
        """
        Shows who holds the GPU and returns the model the user (or the default policy) chose.

        Without a terminal: a server that already has this model is used, otherwise the model is
        loaded partly on the GPU. A server is never asked to switch without the user.

        Returns:
            The loaded model, or None when the user cancelled or nothing worked.
        """
        snapshot = self.snapshot()
        servers = self._servers()
        for line in self._describe(snapshot, servers):
            func.out(line)
        choices = self._choices(error, snapshot, servers)

        if not self.interactive:
            same = [s for s in servers if s.get("model") and self._same_model(s["model"])]
            pick = next((c for c in choices if c.label.startswith("Use the running server: it already has")),
                        choices[-1]) if same else choices[-1]
            func.out(f"      No terminal to ask: {pick.label[0].lower() + pick.label[1:]}.")
            return self._run(pick)

        func.out("      What do you want to do?")
        for n, choice in enumerate(choices, 1):
            func.out(f"        {n}) {choice.label}")
        func.out(f"        {len(choices) + 1}) Cancel")
        while True:
            try:
                answer = self.ask(f"Choice [1]: ").strip() or "1"
            except (EOFError, KeyboardInterrupt):
                answer = str(len(choices) + 1)
            if answer.isdigit() and 1 <= int(answer) <= len(choices) + 1:
                break
            func.out(f"      Type a number from 1 to {len(choices) + 1}.")
        if int(answer) == len(choices) + 1:
            func.out("Cancelled.")
            return None
        return self._run(choices[int(answer) - 1])

    @staticmethod
    def _run(choice: Choice):
        try:
            return choice.run()
        except GpuMemoryError as e:
            func.error(f"{e} Even CPU only did not fit; free some memory and try again.")
        except Exception as e:
            func.error(f"Could not continue: {e}")
        return None
