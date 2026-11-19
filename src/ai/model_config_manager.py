import json
import os
import sys
import argparse

from ai.entities.model_enums import ModelType
import ai.functions as func 
from ai.color import Color, format_text 

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
        generators = {
            ModelType.OLLAMA: ModelConfigManager._generate_ollama_config,
            ModelType.CAUSAL_LM: ModelConfigManager._generate_causal_lm_config,
            ModelType.GGUF: ModelConfigManager._generate_gguf_config,
            ModelType.SEQ2SEQ_LM: ModelConfigManager._generate_seq2seq_lm_config,
            ModelType.GEMINI: ModelConfigManager._generate_gemini_config,
            ModelType.OPEN_AI: ModelConfigManager._generate_openai_config,
            ModelType.JARVIS: ModelConfigManager._generate_jarvis_config,
        }
        generator = generators.get(model_type)
        if generator is None:
            raise ValueError(f"No config template for model type '{model_type.value}'.")
        return generator(model_name)

    @staticmethod
    def _generate_seq2seq_lm_config(model_name):
        """A Hugging Face encoder-decoder model (T5, BART); model_name is its repo id."""
        return {
            "model_name": model_name,
            "model_type": "seq2seq_lm",
            "model_properties": {
                "max_new_tokens": 1024,
                "do_sample": True,
                "temperature": 0.9,
                "top_p": 0.9,
                "top_k": 50,
                "quantization_bits": 0
            }
        }

    @staticmethod
    def _generate_gemini_config(model_name):
        """A Gemini model: GEMINI_API_KEY, or vertex_ai true with gcloud credentials."""
        return {
            "model_name": model_name,
            "model_type": "gemini",
            "model_properties": {
                "n_ctx": 1000000,
                "vertex_ai": False,
                "max_new_tokens": 8192,
                "temperature": 1.0
            }
        }

    @staticmethod
    def _generate_openai_config(model_name):
        """An OpenAI-compatible API (key in AI_API_KEY): base_url empty for OpenAI itself, or another provider's URL."""
        return {
            "model_name": model_name,
            "model_type": "openai",
            "model_properties": {
                "base_url": None,
                "n_ctx": 128000,
                "max_new_tokens": 4096,
                "temperature": 0.5,
                "top_p": 0.95
            }
        }

    @staticmethod
    def _generate_jarvis_config(model_name):
        """A client of a Jarvis Brain Server: server_model is the config the server loads."""
        return {
            "model_name": model_name,
            "model_type": "jarvis",
            "model_properties": {
                "base_url": "http://127.0.0.1:9999",
                "server_model": "default",
                "n_ctx": 24000,
                "max_new_tokens": 8192,
                "temperature": 0.3,
                "top_p": 0.95,
                "top_k": 64
            }
        }

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
            func.debug(f"ERROR: Model configuration file '{filepath}' not found.")
            raise FileNotFoundError(f"Model configuration file '{filepath}' not found.")

        try:
            with open(filepath, 'r') as f:
                model_config = json.load(f)
            return model_config
        except json.JSONDecodeError as e:
            func.debug(f"ERROR: Invalid JSON in '{filepath}'. Please check its format. Error: {e}")
            raise json.JSONDecodeError(f"Invalid JSON in '{filepath}'", e.doc, e.pos)
        except Exception as e:
            func.debug(f"ERROR: Failed to load model config from {filepath}: {e}")
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
        """
        Generates a default configuration structure specifically for GGUF models.

        Args:
            model_name (str): The name of the model.

        Returns:
            dict: The default GGUF configuration dictionary.
        """
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
                "frequency_penalty":1.2,
                "chat_format":None,
                "override_system_by_user_template":False
            }
        }
        
    @staticmethod
    def _generate_causal_lm_config(model_name):
        """
        Generates a default configuration structure specifically for Causal LM models.

        Args:
            model_name (str): The name of the model.

        Returns:
            dict: The default Causal LM configuration dictionary.
        """
        return {
            "model_name": model_name,
            "model_type": 'causal_lm',
            "model_properties": {
                "device_map": "auto",
                "max_new_tokens": 8192,
                "do_sample": True,
                "temperature": 0.8,
                "top_p": 0.95,
                "top_k": 30,
                "presence_penalty":1.1,
                "frequency_penalty":1.1,
                "quantization_bits": 4,
                "chat_format":None,
                "override_system_by_user_template":False
            }
        }
        
    @staticmethod
    def _generate_ollama_config(model_name):
        """
        Generates a default configuration structure specifically for Ollama models.

        Args:
            model_name (str): The name of the model.

        Returns:
            dict: The default Ollama configuration dictionary.
        """
        return {
            "model_name": model_name,
            "model_type": 'ollama',
            "model_properties": {
                "max_new_tokens": 8192,
                "do_sample": True,
                "temperature": 0.8,
                "top_p": 0.95,
                "top_k": 30,
                "presence_penalty":1.1,
                "frequency_penalty":1.1,
                "chat_format":None,
                "override_system_by_user_template":False
                
            }
        }