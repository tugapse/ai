import os
import sys
from typing import Optional, Dict, Any

from services.model_manager import EngineManager
from core.llms.base_llm import ModelParams, BaseModel
from config import ProgramConfig, ProgramSetting
import functions as func

class ModelOrchestrator:
    def __init__(self, config: ProgramConfig):
        self.config = config
        self.llm: Optional[BaseModel] = None
        self.model_params: Dict[str, Any] = {}
        self.model_chat_name: str = "__no_chat_name__"

    def load(self, model_config_name: str, system_prompt: str) -> BaseModel:
        if not model_config_name:
            model_config_name = "default.json"
            
        if not str(model_config_name).endswith(".json"):
            model_config_name = f"{model_config_name}.json"
            
        # --- FIX: Fallback for NoneType folder ---
        folder = self.config.get(ProgramSetting.PATHS_MODEL_CONFIGS)
        if folder is None:
            # Fallback to local project folder if config is missing the path
            root = func.get_root_directory()
            folder = os.path.join(root, "model-config")
            
        filename = os.path.join(folder, model_config_name)

        try:
            model_config_data = EngineManager.load_config(filename) 
            self.model_chat_name = model_config_data["model_name"]

            self.llm = EngineManager.load_model_instance(
                model_config=model_config_data,
                system_prompt=system_prompt
            )

            if not self.llm:
                raise ValueError("ModelManager returned None.")

            self._init_model_params()
            return self.llm

        except Exception as e:
            func.error(f"ModelOrchestrator: Failed to load {filename}: {e}", level="CRITICAL")
            sys.exit(1)

    def _init_model_params(self):
        if self.llm and hasattr(self.llm, 'options'):
            self.model_params = ModelParams(**self.llm.options).to_dict()
        else:
            self.model_params = ModelParams().to_dict()

    def get_params(self) -> Dict[str, Any]:
        return self.model_params

    def get_chat_name(self) -> str:
        return self.model_chat_name