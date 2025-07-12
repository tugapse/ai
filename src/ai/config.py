import json
import logging
import os
from os.path import exists, dirname
import shutil
import pathlib

from typing import TypeVar, Generic, Optional 

T = TypeVar("T")

class ProgramSetting:
    # Core settings already present in your config.py
    MODEL_NAME = "MODEL_NAME"
    SYSTEM_PROMPT_FILE = "SYSTEM_PROMPT_FILE"
    SYSTEM_PROMPT_FOLDER = "SYSTEM_PROMPT_FOLDER" 
    PATHS = "PATHS" 
    USER_PATHS = "USER_PATHS" 
    CHAT_LOG = "CHAT_LOG" 
    TASKS_TEMPLATES = "TASKS_TEMPLATES" 
    SYSTEM_TEMPLATES = "SYSTEM_TEMPLATES" 
    INJECT_TEMPLATES = "INJECT_TEMPLATES" 
    OLLAMA_HOST = "OLLAMA_HOST"
    PRINT_LOG = "PRINT_LOG"
    PRINT_DEBUG = "PRINT_DEBUG"
    PRINT_OUTPUT = "PRINT_OUTPUT"

    # Specific path settings, used for clarity and direct access
    PATHS_LOGS = "PATHS_LOGS"
    PATHS_CHAT_LOG = "PATHS_CHAT_LOG"
    PATHS_TASKS_TEMPLATES = "PATHS_TASKS_TEMPLATES"
    PATHS_SYSTEM_TEMPLATES = "PATHS_SYSTEM_TEMPLATES"
    PATHS_WORKSPACES = "PATHS_WORKSPACES"
    PATHS_INJECT_TEMPLATES = "PATHS_INJECT_TEMPLATES"
    
    PATHS_MODEL_CONFIGS = "PATHS_MODEL_CONFIGS"
    
    ROOT_DIRECTORY = "ROOT_DIRECTORY" 

    PATHS_GENERATED_FILES = "PATHS_GENERATED_FILES" 


    # --- Program Settings for Thinking Logic and Output Control ---
    THINKING_MODE = "THINKING_MODE" 
    PRINT_MODE = "PRINT_MODE" 
    TOKENS_PER_PRINT = "TOKENS_PER_PRINT" 
    ENABLE_THINKING_DISPLAY = "ENABLE_THINKING_DISPLAY" 
    LLM_THINKING_LOG_FILE = "LLM_THINKING_LOG_FILE" 

    MODEL_CONFIG_NAME = "MODEL_CONFIG_NAME"


class ProgramConfig(Generic[T]):

    def __init__(self, config: dict = None) -> None:
        self.config = config if config is not None else {} 
        self.logger = logging.Logger(name=__file__)

    def load_predefined_config(self):
        root: str = os.path.dirname(__file__)
        config_filename: str = os.path.join(root, "config.json")
        default_config = self.__load_to_dict(config_filename)
        
        if default_config is None: 
            self.logger.error("Default config.json not found or invalid. Using empty config.")
            default_config = {}

        # Determine the AI_ASSISTANT_DIRECTORY (user_directory)
        user_directory = os.environ.get("AI_ASSISTANT_DIRECTORY", None)
        if not user_directory:
            user_directory = os.path.join(os.path.expanduser("~"), "Ai")
            
        # Ensure the AI_ASSISTANT_DIRECTORY exists
        os.makedirs(user_directory, exist_ok=True)
        self.logger.info(f"AI Assistant root directory: {user_directory}")


        # Check if config.json exists in that path, if not, copy it
        user_config_filename: str = os.path.join(user_directory, "config.json")
        need_save = False
        if not exists(path=user_config_filename):
            self.logger.info(f"config.json not found in {user_directory}. Copying default config.")
            # Copy default config.json
            shutil.copy(config_filename, user_config_filename)
            self.copy_templates_to_user_dir(user_dir=user_directory) # Copy templates only once here
            need_save = True


        user_config = self.__load_to_dict(user_config_filename, user_directory)
        if user_config: 
            default_config.update(**user_config)

        self.config = default_config
        # Ensure that ROOT_DIRECTORY is set to the resolved user_directory
        self.set(ProgramSetting.ROOT_DIRECTORY, user_directory)
        
        # Ensure PATHS_MODEL_CONFIGS is set if not found in config.json, relative to ROOT_DIRECTORY
        if not self.config.get(ProgramSetting.PATHS_MODEL_CONFIGS):
            self.set(ProgramSetting.PATHS_MODEL_CONFIGS, 
                     os.path.join(self.get(ProgramSetting.ROOT_DIRECTORY), "models"))
        
        # Also ensure other derived paths are set if not in config.json, relative to ROOT_DIRECTORY
        if not self.config.get(ProgramSetting.PATHS_LOGS):
            self.set(ProgramSetting.PATHS_LOGS, os.path.join(self.get(ProgramSetting.ROOT_DIRECTORY), "logs"))
        if not self.config.get(ProgramSetting.PATHS_CHAT_LOG):
            self.set(ProgramSetting.PATHS_CHAT_LOG, os.path.join(self.get(ProgramSetting.PATHS_LOGS), "chat_history"))
        if not self.config.get(ProgramSetting.PATHS_WORKSPACES):
            self.set(ProgramSetting.PATHS_WORKSPACES, os.path.join(self.get(ProgramSetting.ROOT_DIRECTORY), "workspaces"))
        
        # Adding default for PATHS_GENERATED_FILES if it's meant to be distinct from workspaces
        if not self.config.get(ProgramSetting.PATHS_GENERATED_FILES):
            self.set(ProgramSetting.PATHS_GENERATED_FILES, os.path.join(self.get(ProgramSetting.ROOT_DIRECTORY), "generated_files"))

        # Set default template paths if not already configured in config.json
        # These will now point inside the user_directory as templates are copied there
        if user_directory: # Only set if user_directory is established for copies
            if not self.config.get(ProgramSetting.PATHS_SYSTEM_TEMPLATES):
                self.set(ProgramSetting.PATHS_SYSTEM_TEMPLATES, os.path.join(user_directory, "prompts", "system_templates"))
            if not self.config.get(ProgramSetting.PATHS_TASKS_TEMPLATES):
                self.set(ProgramSetting.PATHS_TASKS_TEMPLATES, os.path.join(user_directory, "prompts", "task_templates"))
            if not self.config.get(ProgramSetting.PATHS_INJECT_TEMPLATES):
                self.set(ProgramSetting.PATHS_INJECT_TEMPLATES, os.path.join(user_directory, "prompts", "inject_templates"))
        
        # Set default model config name if not present
        if not self.config.get(ProgramSetting.MODEL_CONFIG_NAME):
            self.set(ProgramSetting.MODEL_CONFIG_NAME, "default_model_config.json")
        
        # Set default Ollama host if not present
        if not self.config.get(ProgramSetting.OLLAMA_HOST):
            self.set(ProgramSetting.OLLAMA_HOST, "http://localhost:11434")

        # Set default thinking/output settings if not present
        if not self.config.get(ProgramSetting.LLM_THINKING_LOG_FILE):
            self.set(ProgramSetting.LLM_THINKING_LOG_FILE, "active_thinking_process.log")
        if not self.config.get(ProgramSetting.THINKING_MODE):
            self.set(ProgramSetting.THINKING_MODE, "progressbar")
        if self.config.get(ProgramSetting.ENABLE_THINKING_DISPLAY) is None: 
            self.set(ProgramSetting.ENABLE_THINKING_DISPLAY, True)
        if not self.config.get(ProgramSetting.PRINT_MODE):
            self.set(ProgramSetting.PRINT_MODE, "every_x_tokens")
        if not self.config.get(ProgramSetting.TOKENS_PER_PRINT):
            self.set(ProgramSetting.TOKENS_PER_PRINT, 10)
        
        # Default for print flags
        if self.config.get(ProgramSetting.PRINT_LOG) is None: 
            self.set(ProgramSetting.PRINT_LOG, True)
        if self.config.get(ProgramSetting.PRINT_DEBUG) is None: 
            self.set(ProgramSetting.PRINT_DEBUG, False)
        if self.config.get(ProgramSetting.PRINT_OUTPUT) is None: 
            self.set(ProgramSetting.PRINT_OUTPUT, True)
        if need_save: 
            self.save_config()
            need_save = False

    def __load_to_dict(self, filename: str, root_dir: Optional[str] = None) -> Optional[dict]: 
        if not exists(path=filename):
            self.logger.level = logging.ERROR
            self.logger.error(f"Configuration file not found: {filename}") 
            return None

        if root_dir is None:
            root_dir = dirname(__file__)
        try:
            with open(filename, 'r', encoding='utf-8') as f: 
                text_content: str = (
                    pathlib.Path(filename)
                    .read_text(encoding='utf-8') 
                    .replace("<root_dir>", root_dir)
                    .replace("/", os.path.sep)
                )
                dict_data: dict = json.loads(text_content) 
                return dict_data
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in config file '{filename}': {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error reading config file '{filename}': {e}")
            return None

    def get(self, key: str, default_value: T = None) -> T:
        """
        Retrieves a configuration value by key.
        Returns default_value if the key is not found.
        """
        return self.config.get(key, default_value)

    def set(self, key: str, value=None) -> None:
        if self.config is None:
            self.config = dict()
        self.config[key] = value

    def copy_templates_to_user_dir(self, user_dir: Optional[str] = None): 
        """
        Copies the contents of the project's 'templates' directory to the user's AI assistant directory.
        Removes the 'templates' folder level in the destination.
        """
        if user_dir is None:
            self.logger.warning("User directory not specified for template copy.")
            return

        project_root_templates_dir = os.path.join(dirname(__file__), "templates") # Adjust if 'config.py' is not directly in 'core'
        
        if not os.path.exists(project_root_templates_dir):
            self.logger.warning(f"Source templates directory not found: {project_root_templates_dir}. Skipping template copy.")
            return

        self.logger.info(f"Copying templates from {project_root_templates_dir} to {user_dir}")

        try:
            # Iterate over each item (file or subdirectory) within the source templates directory
            for item_name in os.listdir(project_root_templates_dir):
                src_item_path = os.path.join(project_root_templates_dir, item_name)
                dest_item_path = os.path.join(user_dir, item_name) # Destination directly in user_dir

                if os.path.isdir(src_item_path):
                    # If it's a directory, copy the entire tree
                    shutil.copytree(src_item_path, dest_item_path, dirs_exist_ok=True)
                elif os.path.isfile(src_item_path):
                    # If it's a file, copy it directly
                    shutil.copy2(src_item_path, dest_item_path) # copy2 preserves metadata
            os.sync()
            self.logger.info("Templates copied successfully.")
        except Exception as e:
            self.logger.error(f"Error copying templates: {e}")

    def save_config(self, filename: Optional[str] = None) -> None:
        """
        Saves the current configuration to a JSON file.

        Args:
            filename (str, optional): The name of the file to save the config to.
                                      If None, defaults to 'config.json' in the ROOT_DIRECTORY.
        """
        if self.config is None:
            self.logger.warning("No configuration data to save.")
            return

        if filename is None:
            # Get the root directory, which should be already determined by load_predefined_config
            root_dir = self.get(ProgramSetting.ROOT_DIRECTORY)
            if not root_dir:
                self.logger.error("ROOT_DIRECTORY is not set. Cannot determine default save path for config.")
                return
            full_filepath = os.path.join(root_dir, "config.json")
        else:
            # If a filename is provided, ensure it ends with .json
            if not filename.lower().endswith(".json"):
                filename += ".json"
            full_filepath = filename # Assume full path if provided

        try:
            # Ensure the directory for the config file exists
            os.makedirs(os.path.dirname(full_filepath), exist_ok=True)
            with open(full_filepath, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
            self.logger.info(f"Configuration saved successfully to: {full_filepath}")
        except Exception as e:
            self.logger.error(f"Error saving configuration to {full_filepath}: {e}")
            raise # Re-raise to indicate failure

    @classmethod
    def load(cls) -> 'ProgramConfig': 
        program_config = ProgramConfig()
        program_config.load_predefined_config()
        ProgramConfig.current = program_config
        return program_config

    current: Optional['ProgramConfig'] = None 
