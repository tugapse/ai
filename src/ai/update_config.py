#!/usr/bin/env python3

import os
import json
import sys
import tempfile

def merge_json_configs(primary_file_path, config_defaults_path):
    """
    Merges configuration from a default JSON file into a primary JSON file.
    Existing fields in the primary file are preserved.
    Missing fields from the default file are added to the primary file.

    Args:
        primary_file_path (str): The path to the primary JSON file (e.g., user's config).
        config_defaults_path (str): The path to the default JSON file (e.g., script's default config).
    """
    print(f"--- Starting JSON Merge Process ---")
    print(f"Primary JSON file path: {primary_file_path}")
    print(f"Default config file path: {config_defaults_path}")

    # 1. Load the primary JSON file
    primary_data = {}
    try:
        if not os.path.exists(primary_file_path):
            print(f"Warning: Primary JSON file '{primary_file_path}' not found. Creating a new one.")
            # If primary file doesn't exist, treat it as an empty object to be filled by defaults
            primary_data = {}
        else:
            with open(primary_file_path, 'r', encoding='utf-8') as f:
                primary_data = json.load(f)
            print(f"Successfully loaded primary JSON from '{primary_file_path}'.")
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format in primary file '{primary_file_path}': {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading primary JSON file '{primary_file_path}': {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Load the default config JSON file
    config_defaults = {}
    try:
        if not os.path.exists(config_defaults_path):
            print(f"Error: Default config file '{config_defaults_path}' not found.", file=sys.stderr)
            sys.exit(1)
        with open(config_defaults_path, 'r', encoding='utf-8') as f:
            config_defaults = json.load(f)
        print(f"Successfully loaded default config from '{config_defaults_path}'.")
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON format in default config file '{config_defaults_path}': {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading default config file '{config_defaults_path}': {e}", file=sys.stderr)
        sys.exit(1)

    # 3. Merge the configurations
    # {**config_defaults, **primary_data} will merge config_defaults first,
    # then primary_data, so primary_data's values will overwrite config_defaults'
    # values for any common keys, effectively preserving existing settings
    # and adding missing ones.
    merged_data = {**config_defaults, **primary_data}
    print("Configuration merged successfully.")

    # 4. Save the merged JSON back to the primary file path
    # Use a temporary file for atomic write to prevent data loss
    try:
        # Get the directory of the target file for the temporary file
        target_dir = os.path.dirname(primary_file_path)
        # Ensure the directory exists
        os.makedirs(target_dir, exist_ok=True)

        with tempfile.NamedTemporaryFile(mode='w', delete=False, encoding='utf-8', dir=target_dir) as tmp_file:
            json.dump(merged_data, tmp_file, indent=4, ensure_ascii=False)
        
        # Atomically replace the original file with the new temporary file
        os.replace(tmp_file.name, primary_file_path)
        print(f"Merged configuration saved successfully to '{primary_file_path}'.")

    except Exception as e:
        print(f"Error saving merged JSON to '{primary_file_path}': {e}", file=sys.stderr)
        # Clean up the temporary file if an error occurred before replacement
        if os.path.exists(tmp_file.name):
            os.remove(tmp_file.name)
        sys.exit(1)

    print("--- JSON Merge Process Completed ---")


if __name__ == "__main__":
    # Get the primary JSON file path from the environment variable
    primary_json_env_path = os.environ.get('AI_ASSISTANT_CONFIG_FILENAME')

    if not primary_json_env_path:
        print("Error: Environment variable 'AI_ASSISTANT_CONFIG_FILENAME' not set.", file=sys.stderr)
        print("Using the default config.json", file=sys.stderr)
        sys.exit(1)

    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Define the path to the default config.json
    default_config_path = os.path.join(script_dir, 'config.json')

    merge_json_configs(primary_json_env_path, default_config_path)