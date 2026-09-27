import os
import sys
from typing import Optional, Dict, Any

import ai.functions as func
from ai.services.engine_manager import EngineManager
from ai.core.llms.base_llm import ModelParams, BaseModel
from ai.services.config_helper import ProgramConfig, ProgramSetting
from ai.tools.tool_registry import ToolRegistry

class ModelOrchestrator:


    def __init__(self, config: ProgramConfig):
        self.config = config
        self.model_params: Dict[str, Any] = {}
        self.model_chat_name: str = "__no_chat_name__"
        self.active_model_name:str=""
        self.llm:Optional[BaseModel] = None

    
    def load(self, model_config_name: str, system_prompt: str, tool_registry:Optional[ToolRegistry] = None, model_config_data: Optional[dict] = None) -> BaseModel:
        if model_config_data and "model_name" in model_config_data:
            model_config_name = model_config_data["model_name"]

        if not model_config_name:
            model_config_name = "default.json"
            
        if not str(model_config_name).endswith(".json"):
            model_config_name = f"{model_config_name}.json"
            
        if model_config_data is None:
            folder = self.config.get(ProgramSetting.PATHS_MODEL_CONFIGS)
            if folder is None:
                # Fallback to local project folder if config is missing the path
                root = func.get_root_directory()
                folder = os.path.join(root, "models")
                
            filename = os.path.join(folder, model_config_name)

            try:
                model_config_data = EngineManager.load_config(filename) 
            except Exception as e:
                func.error(f"ModelOrchestrator: Failed to load {filename}: {e}", level="CRITICAL")
                sys.exit(1)

        if model_config_name != self.active_model_name:
            if self.llm: self.llm.request_shutdown()

        try:
            self.model_chat_name = model_config_data.get("model_name", "No name Found")

            self.llm = EngineManager.load_model_instance(
                model_config=model_config_data,
                system_prompt=system_prompt,
                tool_registry=tool_registry
            )

            if not self.llm:
                raise ValueError("ModelManager returned None.")

            self.active_model_name = model_config_name
            self._init_model_params()
            return self.llm

        except Exception as e:
            func.error(f"ModelOrchestrator: Failed to load model {model_config_name}: {e}", level="CRITICAL")
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