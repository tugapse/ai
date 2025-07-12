# services/model_manager.py

import json
import os
import sys
from typing import Optional 

import functions as func 

from entities.model_enums import ModelType
from color import Color, format_text 

from core.llms import ModelParams, BaseModel, OllamaModel, HuggingFaceModel, T5Model, GGUFImageLLM

class ModelManager:
    """
    Manages the creation, loading, and saving of model configuration files,
    and now also handles the instantiation of model objects.
    """

    @staticmethod
    def generate_default_config(
        model_name: str,
        model_type: ModelType
    ) -> dict:
        """
        Generates a default model configuration dictionary.
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
        """
        if not os.path.exists(filepath):
            func.log(f"Model configuration file '{filepath}' not found.", level="ERROR") 
            raise FileNotFoundError(f"Model configuration file '{filepath}' not found.")

        try:
            with open(filepath, 'r', encoding="utf-8") as f:
                model_config = json.load(f)
            func.log(f"Loaded model config from {filepath}") 
            return model_config
        except json.JSONDecodeError as e:
            func.log(f"Invalid JSON in '{filepath}'. Please check its format. Error: {e}", level="ERROR") 
            raise json.JSONDecodeError(f"Invalid JSON in '{filepath}'", e.doc, e.pos)
        except Exception as e:
            func.log(f"Failed to load model config from {filepath}: {e}", level="ERROR") 
            raise e

    @staticmethod
    def save_config(config: dict, filepath: str):
        """
        Saves a model configuration dictionary to a JSON file.
        """
        try:
            with open(filepath, 'w', encoding="utf-8") as f:
                json.dump(config, f, indent=2)
            func.log(f"Saved model config to {filepath}") 
        except Exception as e:
            func.log(f"Failed to save model config to {filepath}: {e}", level="ERROR") 
            raise e

    @staticmethod
    def load_model_instance(
        model_config: dict,
        system_prompt: str,
        ollama_host: Optional[str] = None
    ) -> Optional[BaseModel]:
        """
        Loads and instantiates an LLM model based on the provided model configuration dictionary.
        """
        model_name = model_config.get("model_name")
        model_type_str = model_config.get("model_type")
        model_properties = model_config.get("model_properties", {})

        if not model_name or not model_type_str:
            func.log("'model_name' or 'model_type' missing in model configuration. Cannot load model.", level="ERROR") 
            return None

        try:
            model_type = ModelType(model_type_str)
        except ValueError:
            func.log(f"Unknown model_type '{model_type_str}' in model configuration.", level="ERROR")
            return None

        func.log(f"Selected model: {model_name} (Type: {model_type.value})") 

        max_new_tokens = model_properties.get("max_new_tokens")
        temperature = model_properties.get("temperature")
        top_p = model_properties.get("top_p")
        top_k = model_properties.get("top_k")
        quantization_bits = model_properties.get("quantization_bits", 0)

        model_params = ModelParams(
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            quantization_bits=quantization_bits
        ).to_dict()

        other_llm_kwargs = {k: v for k, v in model_properties.items()
                            if k not in ["quantization_bits", "n_ctx", "n_gpu_layers", "verbose",
                                         "gguf_filename", "model_repo_id", "do_sample", 
                                         "max_new_tokens", "temperature", "top_p", "top_k"]
                           }

        llm_instance: Optional[BaseModel] = None
        try:
            if model_type == ModelType.CAUSAL_LM:
                llm_instance = HuggingFaceModel(
                    model_name=model_name,
                    system_prompt=system_prompt,
                    quantization_bits=quantization_bits,
                    model_params=model_params,
                    **other_llm_kwargs
                )
                func.log(f"Model '{model_name}' loaded as a Causal Language Model (HuggingFace).") 
            elif model_type == ModelType.SEQ2SEQ_LM:
                llm_instance = T5Model(
                    model_name=model_name,
                    system_prompt=system_prompt,
                    quantization_bits=quantization_bits,
                    model_params=model_params,
                    **other_llm_kwargs
                )
                func.log(f"Model '{model_name}' loaded as a Seq2Seq Language Model (T5-type).") 
            elif model_type == ModelType.OLLAMA:
                if not ollama_host:
                    func.log("Ollama host not provided. Using default 'http://localhost:11434'.", level="WARNING") 

                llm_instance = OllamaModel(
                    model_name=model_name,
                    system_prompt=system_prompt,
                    host=ollama_host,
                    model_params=model_params,
                    **other_llm_kwargs
                )
                func.log(f"Model '{model_name}' loaded as an Ollama Model.") 
            elif model_type == ModelType.GGUF:
                gguf_filename = model_properties.get("gguf_filename")
                model_repo_id = model_properties.get("model_repo_id")
                n_ctx = model_properties.get("n_ctx")
                n_gpu_layers = model_properties.get("n_gpu_layers", -1)
                verbose = model_properties.get("verbose", False)

                if not gguf_filename:
                    func.log("'gguf_filename' is required for 'gguf' model_type in model properties.", level="ERROR") 
                    return None

                llm_instance = GGUFImageLLM(
                    model_name=model_name,
                    gguf_filename=gguf_filename,
                    model_repo_id=model_repo_id,
                    system_prompt=system_prompt,
                    n_gpu_layers=n_gpu_layers,
                    n_ctx=n_ctx,
                    verbose=verbose,
                    model_params=model_params,
                    **other_llm_kwargs
                )
                func.log(f"Model '{model_name}' loaded as a GGUF Image LLM.") 
            else:
                func.log(f"Unhandled model_type '{model_type.value}'.", level="ERROR")
                return None
        except Exception as e:
            func.log(f"Failed to instantiate model '{model_name}': {e}", level="ERROR")
            return None

        return llm_instance

