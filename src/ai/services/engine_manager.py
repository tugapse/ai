# services/model_manager.py

import json
import os
import sys
from typing import Optional, Union 

import ai.functions as func 

from ai.entities.model_enums import ModelType, EngineType

from ai.core.llms.base_llm import ModelParams, BaseModel
from ai.services.process_manager import ProcessManager
from ai.core.llms.load_errors import GpuMemoryError
from ai.tools.tool_registry import ToolRegistry

class EngineManager:
    """
    Manages the creation, loading, and saving of model configuration files,
    and handles the instantiation of model objects with environment checks.
    """

    @staticmethod
    def is_engine_installed(module_type: Union[ModelType,EngineType], module_name: str = "") -> bool:
        """
        Checks the installed_engines.json config manually by stepping up
        from src/ai/services/ to the project root.

        Args:
            module_type: The type of model or engine to check (ModelType or EngineType).
            module_name: An optional name associated with the module type, used for specific checks.

        Returns:
            bool: True if the engine/model is marked as installed in the configuration, False otherwise.
        """
        configured_path = os.environ.get("AI_ENGINE_STATUS_FILE")
        if configured_path:
            config_path = configured_path
        elif getattr(sys, "frozen", False):
            executable_dir = os.path.dirname(os.path.abspath(sys.executable))
            bundled_dir = getattr(sys, "_MEIPASS", executable_dir)
            config_paths = [
                os.path.join(os.path.dirname(executable_dir), "installed_engines.json"),
                os.path.join(executable_dir, "installed_engines.json"),
                os.path.join(bundled_dir, "installed_engines.json"),
            ]
            config_path = next(
                (path for path in config_paths if os.path.isfile(path)),
                config_paths[-1],
            )
        else:
            root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
            config_path = os.path.join(root_dir, "installed_engines.json")
        
        # If the file isn't there, we assume nothing is installed
        if not os.path.exists(config_path):
            return False 

        # Mapping Enums to JSON IDs
        mapping = {
            ModelType.GGUF: "gguf",
            ModelType.OLLAMA: "ollama",
            ModelType.CAUSAL_LM: "transformers",
            ModelType.SEQ2SEQ_LM: "transformers",
            ModelType.OPEN_AI: "openai",
            EngineType.GEMINI_API: "gemini_api",
            EngineType.GEMINI_VERTEX: "gemini_vertex",
            EngineType.VOICE_ENGINE:"voice_engine",
            EngineType.VECTOR_MEMORY:"vector_memory"

        }

        engine_id = mapping.get(module_type)
        
        # Gemini logic: Split API vs Vertex
        if module_type == ModelType.GEMINI and "vertex" in module_name.lower():
            engine_id = "gemini_vertex"

        if not engine_id:
            return True # If it's a type we don't manage, let it through

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                installed_config = json.load(f)
                state = installed_config.get(engine_id, {})
                return state.get("installed", False)
        except Exception:
            return False # Fail safe

    @staticmethod
    def generate_default_config(
        model_name: str,
        model_type: ModelType
    ) -> dict:
        """
        Generates a default model configuration dictionary.

        Args:
            model_name: The name to assign to the model configuration.
            model_type: The type of the model (e.g., GGUF, OPEN_AI).

        Returns:
            dict: A dictionary containing default configuration settings for the model.
        """
        config = {
            "model_name": model_name,
            "model_type": model_type.value,
            "model_properties": {
                "max_new_tokens": 1024,
                "do_sample": True,
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 50,
                "quantization_bits": 0
            }
        }

        if model_type == ModelType.SEQ2SEQ_LM:
            config["model_properties"]["temperature"] = 0.9
            config["model_properties"]["top_p"] = 0.9

        return config

    @staticmethod
    def load_config(filepath: str) -> dict:
        """
        Loads and parses a JSON model configuration file.

        Args:
            filepath: The full path to the JSON configuration file.

        Returns:
            dict: The parsed model configuration dictionary.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            json.JSONDecodeError: If the file content is not valid JSON.
            Exception: For other I/O or reading errors.
        """
        if not os.path.exists(filepath):
            func.error(f"Model configuration file '{filepath}' not found.", level="ERROR") 
            raise FileNotFoundError(f"Model configuration file '{filepath}' not found.")

        try:
            with open(filepath, 'r', encoding="utf-8") as f:
                model_config = json.load(f)
            func.log(f"Loaded model config from {filepath}") 
            return model_config
        except json.JSONDecodeError as e:
            func.error(f"Invalid JSON in '{filepath}'. Please check its format. Error: {e}", level="ERROR") 
            raise json.JSONDecodeError(f"Invalid JSON in '{filepath}'", e.doc, e.pos)
        except Exception as e:
            func.error(f"Failed to load model config from {filepath}: {e}", level="ERROR") 
            raise e

    @staticmethod
    def save_config(config: dict, filepath: str):
        """
        Saves a model configuration dictionary to a JSON file.

        Args:
            config: The dictionary containing the model configuration to save.
            filepath: The destination path for the JSON file.

        Raises:
            Exception: If there is an error during file writing.
        """
        try:
            with open(filepath, 'w', encoding="utf-8") as f:
                json.dump(config, f, indent=2)
            func.log(f"Saved model config to {filepath}") 
        except Exception as e:
            func.error(f"Failed to save model config to {filepath}: {e}", level="ERROR") 
            raise e

    @staticmethod
    def load_model_instance(
        model_config: dict,
        system_prompt: str,
        tool_registry:Optional[ToolRegistry]
    ) -> BaseModel:
        """
        Loads and instantiates an LLM model based on the provided model configuration dictionary.

        This method first checks if the required engine is installed before attempting instantiation.

        Args:
            model_config: The configuration dictionary loaded from a file.
            system_prompt: The system prompt to be used when initializing the model.
            tool_registry: An optional registry containing available tools for the model.

        Returns:
            BaseModel: An instantiated LLM model object.

        Raises:
            ValueError: If the configuration is invalid, the model type is unknown, or the required engine is not installed.
            Exception: For errors during the actual model instantiation process.
        """
        model_name = model_config.get("model_name")
        model_type_str = model_config.get("model_type")
        model_properties = model_config.get("model_properties", {})

        if not model_name or not model_type_str:
            func.log("'model_name' or 'model_type' missing in model configuration. Cannot load model.", level="ERROR") 
            raise ValueError("Invalid model configuration: missing 'model_name' or 'model_type'.")

        try:
            model_type = ModelType(model_type_str)
        except ValueError:
            func.log(f"Unknown model_type '{model_type_str}' in model configuration.", level="ERROR")
            raise ValueError("Invalid model configuration: unknown 'model_type'.")

        # If this returns False, we stop here and avoid the 'Lazy Import' crash.
        if not EngineManager.is_engine_installed(model_type, model_name):
            from ai.color import Color
            message = (
                f"The engine for {Color.YELLOW}{model_type.value}{Color.RESET} is not installed.\n"
                f"Run '{Color.CYAN} ai --install{Color.RESET}' to configure it."
            )
            func.error(message, level="ERROR")
            raise ValueError(f"engine not installed: {model_type.value}")

        func.log(f"Selected model: {model_name} (Type: {model_type.value})") 
        quantization_bits = model_properties.get("quantization_bits", 0)
     
        model_params = ModelParams(**model_properties ).to_dict()

        other_llm_kwargs = {k: v for k, v in model_properties.items()
                            if k not in ["quantization_bits", "n_ctx", "n_gpu_layers", "verbose",
                                         "gguf_filename", "model_repo_id", "do_sample",
                                          "azure_endpoint","api_key_name", "mmproj_filename"]
                           }
        if tool_registry : 
            other_llm_kwargs['tool_registry'] = tool_registry

        llm_instance: Optional[BaseModel] = None
        try:
            if model_type == ModelType.CAUSAL_LM:
                llm_instance = EngineManager._create_causal_lm(model_name, system_prompt, quantization_bits, model_params, other_llm_kwargs)
            elif model_type == ModelType.OLLAMA:
                llm_instance = EngineManager._create_ollama_model(model_name, system_prompt, model_params, other_llm_kwargs)
            elif model_type == ModelType.GGUF:
                llm_instance = EngineManager._create_gguf_model(model_name, system_prompt, model_properties, model_params, other_llm_kwargs)
            elif model_type == ModelType.GEMINI:
                llm_instance = EngineManager._create_gemini_model(model_name, system_prompt, model_params, other_llm_kwargs)
            elif model_type == ModelType.OPEN_AI:
                llm_instance = EngineManager._create_openai_model(model_name, system_prompt, model_params, other_llm_kwargs)
            elif model_type == ModelType.JARVIS:
                # n_ctx is the remote model's window: the agent's context sentinel needs it.
                jarvis_kwargs = dict(other_llm_kwargs)
                if model_properties.get("n_ctx"):
                    jarvis_kwargs["n_ctx"] = model_properties["n_ctx"]
                llm_instance = EngineManager._create_jarvis_model(model_name, system_prompt, model_params, jarvis_kwargs)
            else:
                func.log(f"Unhandled model_type '{model_type.value}'.", level="ERROR")
                raise ValueError("Invalid model configuration: unknown 'model_type'.")
        except GpuMemoryError:
            raise  # not a failure of this config: the caller offers alternatives
        except Exception as e:
            func.error(f"Failed to instantiate model '{model_name}': {e}", level="ERROR")
            raise e

        ProcessManager.set_state("model", model_name)
        return llm_instance

    @staticmethod
    def _create_causal_lm(model_name: str, system_prompt: str, quantization_bits: int, model_params: dict, other_llm_kwargs: dict) -> BaseModel:
        """
        Instantiates a HuggingFaceModel for Causal Language Models.

        Args:
            model_name: The name of the model.
            system_prompt: The system prompt.
            quantization_bits: The quantization level.
            model_params: Dictionary of model parameters.
            other_llm_kwargs: Additional keyword arguments for the model.

        Returns:
            BaseModel: The instantiated HuggingFaceModel.
        """
        from ai.core.llms.huggingface_model import HuggingFaceModel
        llm_instance = HuggingFaceModel(
            model_name=model_name,
            system_prompt=system_prompt,
            quantization_bits=quantization_bits,
            model_params=model_params,
            **other_llm_kwargs
        )
        func.log(f"Model '{model_name}' loaded as a Causal Language Model (HuggingFace).")
        return llm_instance

    @staticmethod
    def _create_ollama_model(model_name: str, system_prompt: str, model_params: dict, other_llm_kwargs: dict) -> BaseModel:
        """
        Instantiates an OllamaModel.

        Args:
            model_name: The name of the model.
            system_prompt: The system prompt.
            model_params: Dictionary of model parameters.
            other_llm_kwargs: Additional keyword arguments for the model.

        Returns:
            BaseModel: The instantiated OllamaModel.
        """
        from ai.core.llms.ollama_model import OllamaModel
        llm_instance = OllamaModel(
            model_name=model_name,
            system_prompt=system_prompt,
            model_params=model_params,
            **other_llm_kwargs
        )
        func.log(f"Model '{model_name}' loaded as an Ollama Model.")
        return llm_instance

    @staticmethod
    def _create_gguf_model(model_name: str, system_prompt: str, model_properties: dict, model_params: dict, other_llm_kwargs: dict) -> BaseModel:
        """
        Instantiates a GGUFImageLLM, handling necessary logging setup for llama_cpp.

        Args:
            model_name: The name of the model.
            system_prompt: The system prompt.
            model_properties: The full model properties dictionary.
            model_params: Dictionary of model parameters.
            other_llm_kwargs: Additional keyword arguments for the model.

        Returns:
            BaseModel: The instantiated GGUFImageLLM.

        Raises:
            ValueError: If 'gguf_filename' is missing from model properties.
        """
        # Importing gguf_model installs llama.cpp's silent log callback, kept alive at module level.
        # Do not install one here: a callback local to this function is freed when it returns while
        # llama.cpp keeps the pointer, so the next native log (e.g. llama_free on unload) crashes.
        from ai.core.llms.gguf_model import GGUFImageLLM

        gguf_filename = model_properties.get("gguf_filename")
        model_repo_id = model_properties.get("model_repo_id") or 'default'
        n_ctx = model_properties.get("n_ctx") or 2048
        n_gpu_layers = model_properties.get("n_gpu_layers", -1)
        verbose = model_properties.get("verbose", False)

        if not gguf_filename:
            func.log("'gguf_filename' is required for 'gguf' model_type in model properties.", level="ERROR") 
            raise ValueError("Invalid model configuration: missing 'gguf_filename'.")
        from ai.core.llms.gguf_model import GGUFImageLLM
        llm_instance = GGUFImageLLM(
            model_name=model_name,
            gguf_filename=gguf_filename,
            model_repo_id=model_repo_id,
            system_prompt=system_prompt,
            n_gpu_layers=n_gpu_layers,
            n_ctx=n_ctx,
            verbose=verbose,
            model_params=model_params,
            mmproj_filename=model_properties.get("mmproj_filename", ""),
            **other_llm_kwargs
        )
        func.log(f"Model '{model_name}' loaded as a GGUF Image LLM.")
        return llm_instance

    @staticmethod
    def _create_gemini_model(model_name: str, system_prompt: str, model_params: dict, other_llm_kwargs: dict) -> BaseModel:
        """
        Instantiates a GeminiAPIModel.

        Args:
            model_name: The name of the model.
            system_prompt: The system prompt.
            model_params: Dictionary of model parameters.
            other_llm_kwargs: Additional keyword arguments for the model, including 'vertex_ai'.

        Returns:
            BaseModel: The instantiated GeminiAPIModel.
        """
        from ai.core.llms.gemini import GeminiAPIModel
        llm_instance = GeminiAPIModel(
            model_name=model_name,
            system_prompt=system_prompt,
            model_params=model_params,
            use_vertex=other_llm_kwargs.get("vertex_ai", False),
            **other_llm_kwargs
        )
        func.log(f"Model '{model_name}' loaded as a Gemini Model.")
        return llm_instance

    @staticmethod
    def _create_openai_model(model_name: str, system_prompt: str, model_params: dict, other_llm_kwargs: dict) -> BaseModel:
        """
        Instantiates an OpenAIAPIModel.

        Args:
            model_name: The name of the model.
            system_prompt: The system prompt.
            model_params: Dictionary of model parameters.
            other_llm_kwargs: Additional keyword arguments for the model.

        Returns:
            BaseModel: The instantiated OpenAIAPIModel.
        """
        from ai.core.llms.open_ai import OpenAIAPIModel
        llm_instance = OpenAIAPIModel(
            model_name=model_name,
            system_prompt=system_prompt,
            model_params=model_params,
            **other_llm_kwargs
        )
        func.log(f"Model '{model_name}' loaded as an OpenAI Model.")
        return llm_instance

    @staticmethod
    def _create_jarvis_model(model_name: str, system_prompt: str, model_params: dict, other_llm_kwargs: dict) -> BaseModel:
        """
        Instantiates a JarvisAiModel.

        Args:
            model_name: The name of the model.
            system_prompt: The system prompt.
            model_params: Dictionary of model parameters.
            other_llm_kwargs: Additional keyword arguments for the model.

        Returns:
            BaseModel: The instantiated JarvisAiModel.
        """
        from ai.core.llms.jarvis import JarvisAiModel
        llm_instance = JarvisAiModel(
            model_name=model_name,
            system_prompt=system_prompt,
            model_params=model_params,
            **other_llm_kwargs
        )
        func.log(f"Model '{model_name}' loaded as a JARVIS Model.")
        return llm_instance