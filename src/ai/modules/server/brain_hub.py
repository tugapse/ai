import os
from typing import Optional
import functions as func
from config import ProgramConfig, ProgramSetting
from services.history_manager import HistoryManager
from services.model_orchestrator import ModelOrchestrator

class BrainHub:
    def __init__(self, config: ProgramConfig, history_manager: HistoryManager):
        self.config = config
        self.orchestrator = ModelOrchestrator(config)
        self.current_model_id: Optional[str] = None
        self.history = history_manager
    
    def route_memory(self, session_filepath: str):
        """Instructs the History Manager to hot-swap the active JSON file."""
        if self.history:
            self.history.switch_active_session(session_filepath)
    
    def get_brain(self, model_id: str, system_prompt: str):
        """
        Ensures the requested model is loaded. 
        If a different model is active, it unloads it first to clear VRAM.
        """
        # 1. Check if we need to swap
        if self.current_model_id and self.current_model_id != model_id:
            func.log(f"BrainHub: Swapping {self.current_model_id} -> {model_id}")
            self.unload_brain()

        # 2. Load the model if it's not already 'Hot'
        if not self.orchestrator.llm:
            # Note: ModelOrchestrator.load handles the heavy lifting
            self.orchestrator.load(model_id, system_prompt)
            self.current_model_id = model_id
            func.log(f"BrainHub: {model_id} is now HOT.")

        return self.orchestrator.llm

    def unload_brain(self):
        """Clears the GPU memory by calling the model's specific unload method."""
        if self.orchestrator.llm:
            func.log(f"BrainHub: Unloading {self.current_model_id}...")
            
            # Directly call the model's specific unload method.
            # This is a blocking call that ensures all C++ resources and threads
            # are properly cleaned up before proceeding, preventing race conditions.
            self.orchestrator.llm.unload()
            
            # Now that unload is complete, we can safely clear the references.
            self.orchestrator.llm = None
            self.current_model_id = None

    def list_available_models(self) -> list:
        """Scans the model-config folder for available JSON brains."""
        folder = self.config.get(ProgramSetting.PATHS_MODEL_CONFIGS)
        if not folder or not os.path.exists(folder):
            return []
        
        return [f.replace(".json", "") for f in os.listdir(folder) if f.endswith(".json")]

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
            "usage_percent": round((stats.prompt_count / stats.max_context_window * 100), 2) if stats.max_context_window > 0 else 0
        }