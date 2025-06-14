import json
import os
import sys
import argparse

from core.llms.model_enums import ModelType
from color import Color, format_text # Assuming these are available as in program.py
import functions as func # Assuming functions.py is available for logging


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
        config = {
            "model_name": model_name,
            "model_type": model_type.value,
            "model_properties": {
                "max_new_tokens": 1024,
                "do_sample": True,
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 50,
                "quantize": False
            }
        }

        # Model-type specific adjustments can still be made if necessary
        if model_type == ModelType.SEQ2SEQ_LM:
            # T5 models (seq2seq) might prefer slightly different defaults
            config["model_properties"]["temperature"] = 0.9
            config["model_properties"]["top_p"] = 0.9

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

# --- Command-Line Interface for Generating Config Files ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate a default model configuration file.",
        formatter_class=argparse.RawTextHelpFormatter # For better help text formatting
    )

    parser.add_argument(
        "-m", "--model-name",
        required=True,
        type=str,
        help="The name of the model (e.g., 'meta-llama/Llama-2-7b-chat-hf')."
    )
    parser.add_argument(
        "-t", "--model-type",
        required=True,
        type=str,
        choices=[t.value for t in ModelType],
        help="The architectural type of the model."
    )
    parser.add_argument(
        "-o", "--output-file",
        required=True,
        type=str,
        help="The path where the generated JSON configuration file will be saved."
    )

    args = parser.parse_args()

    try:
        

        # Convert string argument back to Enum member
        model_type_enum = ModelType(args.model_type)

        # Log the action
        print(format_text(
            f"--- Generating config for {args.model_name} ---", Color.BLUE
        ))

        # Generate the configuration dictionary
        new_config = ModelConfigManager.generate_default_config(
            model_name=args.model_name,
            model_type=model_type_enum
        )

        # Save the configuration to the specified file
        ModelConfigManager.save_config(new_config, args.output_file)

        # Print success message to the console
        success_message = format_text(
            f"\nSuccessfully generated and saved configuration to: ", Color.GREEN
        ) + format_text(f"{args.output_file}", Color.YELLOW)
        print(success_message)
        print(json.dumps(new_config, indent=2))


    except ValueError as e:
        # This will catch errors if the string from args doesn't match an Enum value
        error_msg = format_text(f"ERROR: Invalid parameter value provided. {e}", Color.RED)
        print(error_msg)
        print(error_msg, file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        error_msg = format_text(f"An unexpected error occurred: {e}", Color.RED)
        print(f"ERROR: {error_msg}")
        print(error_msg, file=sys.stderr)
        sys.exit(1)