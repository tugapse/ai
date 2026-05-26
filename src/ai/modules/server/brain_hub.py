import os
from typing import Optional
import ai.functions as func
from ai.config import ProgramConfig, ProgramSetting
from ai.services.history_manager import HistoryManager
from ai.services.model_orchestrator import ModelOrchestrator


class BrainHub:
    def __init__(self, config: ProgramConfig):
        self.config = config
        self.orchestrator = ModelOrchestrator(config)
        self.history_file: str = ""
        self.current_model_id: Optional[str] = None
        self.history = self.new_history(None, "default", None)
        

    def new_history(self, session_title: Optional[str], session_id: str, session_folder: Optional[str]) -> dict:
        """Initializes a fresh history structure."""
        return {
            "session_id": session_id,
            "session_folder": session_folder,
            "session_title": session_title,
            "messages": [],
            "last_updated": None,
        }

    def route_memory(self, session_filepath: str, session_title: Optional[str], session_id: str, session_folder: Optional[str]):
        """Instructs the History Manager to hot-swap the active JSON file."""
        self.history_file = session_filepath
        self.history = self.new_history(session_title, session_id, session_folder)
        self.load_history_from_json(session_filepath)

    def add_history_message(self, role: str, content: str):
            """Convenience method to add messages to the history from the API endpoints."""
            self.history["messages"].append(
                {"role": role, "content": content}
            )
            self.history["last_updated"] = self.get_timestamp()
            self.save_history_to_json(self.history_file)


    def load_history_from_json(self, filepath: str):
        """Loads a specific JSON file into the History Manager."""
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
        """Saves the current history to a JSON file."""
        import json

        with open(filepath, "w") as f:
            json.dump(self.history, f, indent=4)
        func.log(f"BrainHub: Memory saved to {filepath}")

   

    def get_timestamp(self) -> str:
        """Generates a timestamp string for history entries."""
        from datetime import datetime

        return datetime.now().isoformat()

    def get_brain(self, model_id: str, system_prompt: str):
        """
        Ensures the requested model is loaded.
        If a different model is active, it unloads it first to clear VRAM.
        """
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
            self.orchestrator.load(model_id, system_prompt)
            self.current_model_id = model_id
            func.log(f"BrainHub: {model_id} is now HOT.")

        return self.orchestrator.llm

    def unload_brain(self):
        """Clears the GPU memory by calling the model's specific unload method."""
        if self.orchestrator.llm:
            func.log(f"BrainHub: Unloading {self.current_model_id}...")

            self.orchestrator.llm.unload()

            self.orchestrator.llm = None
            self.current_model_id = None

    def list_available_models(self) -> list:
        """Scans the model-config folder for available JSON brains."""
        folder = self.config.get(ProgramSetting.PATHS_MODEL_CONFIGS)
        if not folder or not os.path.exists(folder):
            return []

        return [
            f.replace(".json", "") for f in os.listdir(folder) if f.endswith(".json")
        ]

    def get_stats(self) -> dict:
        """Extracts the 'fuel gauge' stats from the active model."""
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
