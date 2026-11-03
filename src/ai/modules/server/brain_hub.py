import os
from typing import Optional
import ai.functions as func
from ai.config import ProgramConfig, ProgramSetting
from ai.services.history_manager import HistoryManager
from ai.services.model_orchestrator import ModelOrchestrator


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

    def add_history_message(self, role: str, content: str):
            """
            Convenience method to add messages to the history from the API endpoints.

            Updates the history in memory and immediately saves the updated state
            to the active JSON file.

            Args:
                role: The role of the message (e.g., 'user', 'assistant').
                content: The textual content of the message.
            """
            self.history["messages"].append(
                {"role": role, "content": content}
            )
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
                        func.log(f"BrainHub: Memory loaded from {filepath}")
                    else:
                        func.log(
                            f"BrainHub: Invalid session file format at {filepath}. Starting fresh.",
                            level="WARN",
                        )
                        self.history["messages"] = [] # Clear messages
                        self.history["last_updated"] = None # Reset last updated timestamp
            except json.JSONDecodeError:
                func.log(
                    f"BrainHub: Corrupted session file at {filepath}. Starting fresh.",
                    level="ERROR",
                )
                self.history["messages"] = [] # Clear messages
                self.history["last_updated"] = None # Reset last updated timestamp
        else:
            func.log(
                f"BrainHub: No session found at {filepath}. Starting fresh.",
                level="WARN",
            )
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
        func.log(f"BrainHub: Memory saved to {filepath}")

   

    def get_timestamp(self) -> str:
        """
        Generates a standardized ISO format timestamp string for history entries.

        Returns:
            A string representing the current time in ISO format.
        """
        from datetime import datetime

        return datetime.now().isoformat()

    def get_brain(self, model_id: str, system_prompt: str, model_config_data: Optional[dict] = None):
        """
        Ensures the requested model is loaded and active for interaction.

        If a different model is currently active, it is unloaded first to free up
        GPU resources before loading the new model. It also updates the system
        prompt if the model is already loaded.

        Args:
            model_id: The identifier of the desired model.
            system_prompt: The system-level instruction prompt for the model.
            model_config_data: Optional dictionary containing model configuration details,
                                which may override the model_id.

        Returns:
            The active LLM object instance from the ModelOrchestrator.
        """
        if model_config_data and "model_name" in model_config_data:
            model_id = model_config_data["model_name"]

        if self.current_model_id and self.current_model_id != model_id:
            func.log(f"BrainHub: Swapping {self.current_model_id} -> {model_id}")
            self.unload_brain()

        if self.orchestrator.llm:
            if getattr(self.orchestrator.llm, "system_prompt", None) != system_prompt:
                func.log(
                    f"BrainHub: Updating system prompt for loaded model '{model_id}'.",
                    level="DEBUG",
                )
                self.orchestrator.llm.system_prompt = system_prompt
            return self.orchestrator.llm

        if not self.orchestrator.llm:
            self.orchestrator.load(
                model_config_name=model_id, 
                system_prompt=system_prompt, 
                model_config_data=model_config_data
            )
            self.current_model_id = model_id
            func.log(f"BrainHub: {model_id} is now HOT.")

        return self.orchestrator.llm

    def unload_brain(self):
        """
        Clears the GPU memory by calling the model's specific unload method.

        This resets the active model state and clears the current model ID.
        """
        if self.orchestrator.llm:
            func.log(f"BrainHub: Unloading {self.current_model_id}...")

            self.orchestrator.llm.unload()

            self.orchestrator.llm = None
            self.current_model_id = None

    def list_available_models(self) -> list:
        """
        Scans the model-config folder for available JSON brains.

        Returns:
            A list of model names (without the .json extension) found in the configuration directory.
        """
        folder = self.config.get(ProgramSetting.PATHS_MODEL_CONFIGS)
        if not folder or not os.path.exists(folder):
            return []

        return [
            f.replace(".json", "") for f in os.listdir(folder) if f.endswith(".json")
        ]

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