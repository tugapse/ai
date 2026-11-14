import os
import sys
from typing import Optional, Dict, Any

import ai.functions as func
from ai.services.directory_manager import DirectoryManager
from ai.services.engine_manager import EngineManager
from ai.core.llms.load_errors import GpuMemoryError
from ai.core.llms.base_llm import ModelParams, BaseModel
from ai.services.config_helper import ProgramConfig, ProgramSetting
from ai.tools.tool_registry import ToolRegistry

class ModelOrchestrator:
    """
    Manages the loading, configuration, and lifecycle of various language models.

    This orchestrator handles locating model configuration files (system or user-specific),
    loading the appropriate LLM instance via the EngineManager, and tracking the
    active model's parameters and chat identity.
    """

    def __init__(self, config: ProgramConfig):
        """
        Initializes the ModelOrchestrator.

        Args:
            config: The global program configuration object.
        """
        self.config = config
        self.model_params: Dict[str, Any] = {}
        self.model_chat_name: str = "__no_chat_name__"
        self.active_model_name:str=""
        self.llm:Optional[BaseModel] = None

    
    @staticmethod
    def config_folders() -> list:
        """The model config folders, in priority order: user models, then system models."""
        directory = DirectoryManager()
        return [directory.get_user_models_directory(), directory.get_system_models_directory()]

    @staticmethod
    def find_config_file(model_config_name: Optional[str]) -> Optional[str]:
        """
        Returns the path of a model config file, or None when it does not exist.

        The name may point into a subfolder ("agents/lite"). The user models folder wins over
        the system one. ``name`` and ``name.json`` are the same config. A name that escapes the
        models folders ("../x", an absolute path) is never found.
        """
        name = (model_config_name or "default").strip().replace("\\", "/")
        if not name.endswith(".json"):
            name = f"{name}.json"
        if os.path.isabs(name) or ".." in name.split("/"):
            return None
        for folder in ModelOrchestrator.config_folders():
            root = os.path.realpath(folder)
            path = os.path.realpath(os.path.join(root, name))
            if path.startswith(root + os.sep) and os.path.isfile(path):
                return path
        return None

    @staticmethod
    def list_config_files() -> Dict[str, str]:
        """
        Every model config, including subfolders: ``{key: path}``.

        The key is the path under the models folder without ``.json``, with ``/`` separators
        ("small", "agents/lite"); it is what ``find_config_file`` accepts. A user config hides a
        system config with the same key.
        """
        configs: Dict[str, str] = {}
        for folder in reversed(ModelOrchestrator.config_folders()):
            if not os.path.isdir(folder):
                continue
            for dirpath, dirnames, filenames in os.walk(folder):
                dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
                for filename in filenames:
                    if filename.endswith(".json"):
                        path = os.path.join(dirpath, filename)
                        key = os.path.relpath(path, folder)[:-len(".json")].replace(os.sep, "/")
                        configs[key] = path
        return dict(sorted(configs.items()))

    def load(self, model_config_name: str, system_prompt: str, tool_registry:Optional[ToolRegistry] = None, model_config_data: Optional[dict] = None, raise_errors: bool = False, gpu_fallback: bool = False) -> BaseModel:
        """
        Loads a specific language model instance based on configuration.

        It resolves the configuration file path, loads the necessary data,
        and initializes the LLM object. If a model is already active, it is shut down
        before loading the new one.

        Args:
            model_config_name: The base name of the model configuration file (e.g., "gpt4").
            system_prompt: The system-level prompt to be used when initializing the model.
            tool_registry: An optional registry containing available tools for the model.
            model_config_data: Optional pre-loaded configuration dictionary. If provided,
                               it overrides the need to load from disk.
            raise_errors: Raise the error instead of exiting (the server must keep running).
            gpu_fallback: With ``raise_errors``, a model that does not fit in the free GPU memory is
                          loaded partly on the GPU (down to CPU only) instead of raising.

        Returns:
            The initialized BaseModel instance of the loaded LLM.

        Raises:
            SystemExit: If configuration loading or model initialization fails critically
                        (only when ``raise_errors`` is False).
        """
        if model_config_data and "model_name" in model_config_data:
            model_config_name = model_config_data["model_name"]

        if not model_config_name:
            model_config_name = "default.json"
            
        if not str(model_config_name).endswith(".json"):
            model_config_name = f"{model_config_name}.json"
            
        if model_config_data is None:
            filename = self.find_config_file(model_config_name) or os.path.join(
                DirectoryManager().get_system_models_directory(), model_config_name)
            try:
                model_config_data = EngineManager.load_config(filename)
            except Exception as e:
                if raise_errors:
                    raise
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

        except GpuMemoryError as e:
            self.llm = None
            self.active_model_name = ""
            if raise_errors and not gpu_fallback:
                raise
            from ai.services.gpu_advisor import GpuAdvisor
            advisor = GpuAdvisor(model_config_name, model_config_data, system_prompt, tool_registry,
                                 interactive=False if raise_errors else None)
            if raise_errors:
                # Unattended (the server): no one to ask, so load what fits; raises if nothing does.
                llm = advisor.load_partial(e)
            else:
                # The GPU is full: show who holds it and offer alternatives instead of failing.
                llm = advisor.resolve(e)
                if llm is None:
                    sys.exit(1)
            self.llm = llm
            self.active_model_name = model_config_name
            self._init_model_params()
            return self.llm

        except Exception as e:
            self.llm = None
            self.active_model_name = ""
            if raise_errors:
                raise
            func.error(f"ModelOrchestrator: Failed to load model {model_config_name}: {e}", level="CRITICAL")
            sys.exit(1)

    def _init_model_params(self):
        """
        Initializes the internal model parameters dictionary based on the currently active LLM's options.

        If the LLM has options, it extracts them into ModelParams; otherwise, it uses default parameters.
        """
        if self.llm and hasattr(self.llm, 'options'):
            self.model_params = ModelParams(**self.llm.options).to_dict()
        else:
            self.model_params = ModelParams().to_dict()

    def get_params(self) -> Dict[str, Any]:
        """
        Retrieves the current set of parameters associated with the active model.

        Returns:
            A dictionary containing the model's configuration parameters.
        """
        return self.model_params

    def get_chat_name(self) -> str:
        """
        Retrieves the designated chat name for the currently active model.

        Returns:
            The string identifier for the model's chat context.
        """
        return self.model_chat_name