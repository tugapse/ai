import json
import os
import sys
import argparse

from entities.model_enums import ModelType
from color import Color, format_text 
import functions as func 

class ModelConfigManager:
    """
    Manages the creation, loading, and saving of model configuration files.
    """

    @staticmethod
    def generate_default_config(
        model_name: str,
        model_type: ModelType
    ) -> dict:
        """
        Generates a default model configuration dictionary based on the specified
        model name and model type.

        Args:
            model_name (str): The specific name of the model.
            model_type (ModelType): The architectural type of the model (e.g., Causal LM, Seq2Seq LM).

        Returns:
            dict: A dictionary representing the default model configuration.
        """
        config = {}
        if model_type == ModelType.OLLAMA:
            config = ModelConfigManager._generate_ollama_config(model_name)
        elif model_type == ModelType.CAUSAL_LM:
            config = ModelConfigManager._generate_causal_lm_config(model_name)
        elif model_type == ModelType.GGUF:
            config = ModelConfigManager._generate_gguf_config(model_name)
        
        return config

    @staticmethod
    def load_config(filepath: str) -> dict:
        """
        Loads and parses a JSON model configuration file.

        Args:
            filepath (str): The path to the model configuration JSON file.

        Returns:
            dict: The loaded model configuration.

        Raises:
            FileNotFoundError: If the specified file does not exist.
            json.JSONDecodeError: If the file contains invalid JSON.
            Exception: For other loading errors.
        """
        if not os.path.exists(filepath):
            print(f"ERROR: Model configuration file '{filepath}' not found.")
            raise FileNotFoundError(f"Model configuration file '{filepath}' not found.")

        try:
            with open(filepath, 'r') as f:
                model_config = json.load(f)
            print(f"INFO: Loaded model config from {filepath}")
            return model_config
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON in '{filepath}'. Please check its format. Error: {e}")
            raise json.JSONDecodeError(f"Invalid JSON in '{filepath}'", e.doc, e.pos)
        except Exception as e:
            print(f"ERROR: Failed to load model config from {filepath}: {e}")
            raise e

    @staticmethod
    def save_config(config: dict, filepath: str):
        """
        Saves a model configuration dictionary to a JSON file.

        Args:
            config (dict): The model configuration dictionary to save.
            filepath (str): The path where the JSON file will be saved.
        """
        try:
            with open(filepath, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"INFO: Saved model config to {filepath}")
        except Exception as e:
            print(f"ERROR: Failed to save model config to {filepath}: {e}")
            raise e
    
    @staticmethod
    def _generate_gguf_config(model_name):
        return {
            "model_name": model_name,
            "model_type": 'gguf',
            "model_properties": {
                "gguf_filename": "gguf_filename",
                "model_repo_id": "model_repo_id",
                "n_gpu_layers": -1,
                "n_ctx": 8192,
                "verbose": False,
                "max_new_tokens": 4096,
                "temperature": 0.3,
                "top_p": 0.95,
                "top_k":50,
                "presence_penalty": 1.1,
                "frequency_penalty":1.2
            }
        }
        
    @staticmethod
    def _generate_causal_lm_config(model_name):
        return {
            "model_name": model_name,
            "model_type": 'causal_lm',
            "model_properties": {
                "max_new_tokens": 8192,
                "do_sample": True,
                "temperature": 0.1,
                "top_p": 0.95,
                "top_k": 10,
                "presence_penalty":1.5,
                "frequency_penalty":1.2,
                "quantization_bits": 8
            }
        }
        
    @staticmethod
    def _generate_ollama_config(model_name):
        return {
            "model_name": model_name,
            "model_type": 'ollama',
            "model_properties": {
                "max_new_tokens": 8192,
                "do_sample": True,
                "temperature": 0.1,
                "top_p": 0.95,
                "top_k": 10,
                "presence_penalty":1.5,
                "frequency_penalty":1.2
                
            }
        }