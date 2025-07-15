class LLMParamsConfigurator:
    """
    A class to manage and prepare LLM generation parameters for different model types.

    It holds a set of common LLM generation properties and provides a method
    to map and filter user-provided parameters to be compatible with
    specific model ecosystems like Hugging Face Transformers or GGUF loaders.
    """

    def __init__(self):
        # Common LLM generation parameters with their typical default values.
        # Note: Actual defaults can vary slightly between models and libraries.
        self.available_properties = {
            "temperature": 1.0,
            "top_p": 1.0,
            "top_k": 50,
            "presence_penalty": 0.0,
            "frequency_penalty": 0.0,
            "max_tokens": 16,
            "do_sample": True,
            "num_beams": 1,
            "no_repeat_ngram_size": 0,
            "stop_sequences": [],
            "early_stopping": False,
            "length_penalty": 1.0,
            "num_return_sequences": 1,
            "bad_words_ids": [],
            "eos_token_id": None,
            "min_length": 0
        }

        # Defines parameter compatibility and name mappings for different model types.
        # Keys are internal common names, values are the target library's parameter names.
        # This is a simplified mapping; real-world libraries might have more specific nuances.
        self.model_param_compatibility = {
            "huggingface": {
                "temperature": "temperature",
                "top_p": "top_p",
                "top_k": "top_k",
                "presence_penalty": "presence_penalty",
                "frequency_penalty": "frequency_penalty",
                "max_tokens": "max_new_tokens",  # Hugging Face often uses 'max_new_tokens'
                "do_sample": "do_sample",
                "num_beams": "num_beams",
                "no_repeat_ngram_size": "no_repeat_ngram_size",
                "stop_sequences": "stop_strings", # Hugging Face uses 'stop_strings' or 'stopping_criteria'
                "early_stopping": "early_stopping",
                "length_penalty": "length_penalty",
                "num_return_sequences": "num_return_sequences",
                "bad_words_ids": "bad_words_ids",
                "eos_token_id": "eos_token_id",
                "min_length": "min_length"
            },
            "gguf": {  # Parameters commonly supported by llama.cpp/llama-cpp-python for GGUF models
                "temperature": "temperature",
                "top_p": "top_p",
                "top_k": "top_k",
                "presence_penalty": "presence_penalty",
                "frequency_penalty": "frequency_penalty",
                "max_tokens": "max_tokens",  # GGUF loaders often use 'max_tokens' directly
                "do_sample": "do_sample",
                "num_beams": "n_gpu_layers", # Example mapping for some GGUF loaders' 'num_beams' equivalent
                "stop_sequences": "stop",    # GGUF/llama.cpp often uses 'stop'
            }
        }

    def prepare_llm_params(self, model_type: str, user_params: dict = {}) -> dict:
        """
        Maps and filters user-provided LLM generation parameters for a specific model type.

        This function takes a dictionary of desired parameters (`user_params`) and
        returns a new dictionary containing only the parameters that are valid for
        the specified `model_type` and were provided by the user. Parameter names
        are mapped to the target library's conventions where necessary.

        Args:
            model_type (str): The type of model to prepare parameters for.
                              Currently supported: 'huggingface', 'gguf'.
            user_params (dict): A dictionary of parameters provided by the user.
                                Keys should match `self.available_properties`.

        Returns:
            dict: A dictionary of parameters valid and mapped for the specified model type.
                  Only includes parameters present in `user_params` and supported by `model_type`.

        Raises:
            ValueError: If an unsupported `model_type` is provided.
        """
        if model_type not in self.model_param_compatibility:
            raise ValueError(
                f"Unsupported model type: '{model_type}'. "
                f"Supported types are: {list(self.model_param_compatibility.keys())}"
            )

        param_map = self.model_param_compatibility[model_type]
        prepared_params = {}

        for user_param_name, user_param_value in user_params.items():
            if user_param_name in self.available_properties:
                if user_param_name in param_map:
                    target_param_name = param_map[user_param_name]
                    prepared_params[target_param_name] = user_param_value
                else:
                    print(f"Warning: Parameter '{user_param_name}' is not typically supported by '{model_type}' models and will be ignored.")
            else:
                print(f"Warning: Unknown parameter '{user_param_name}' and will be ignored.")

        return prepared_params