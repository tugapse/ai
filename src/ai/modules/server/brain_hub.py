import os
import functions as func
from services.model_orchestrator import ModelOrchestrator
from config import ProgramConfig, ProgramSetting

class BrainHub:
    def __init__(self, config: ProgramConfig):
        self.config = config
        self.orchestrator = ModelOrchestrator(config)
        self.current_model_id: Optional[str] = None

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
        """Clears the GPU memory and joins threads."""
        if self.orchestrator.llm:
            func.log(f"BrainHub: Unloading {self.current_model_id}...")
            self.orchestrator.llm.request_shutdown() # Set event, join thread, clean cache
            self.orchestrator.llm = None
            self.current_model_id = None
            func.log("BrainHub: VRAM cleared.")

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