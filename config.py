import json
import logging
import os
from os.path import exists, dirname
import shutil
import pathlib

from typing import TypeVar, Generic

T = TypeVar("T")

class ProgramSetting:
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
    PRINT_OUTPUT = "PRINT_OUTPUT"

    PATHS_LOGS = "PATHS_LOGS"
    PATHS_CHAT_LOG = "PATHS_CHAT_LOG"
    PATHS_TASKS_TEMPLATES = "PATHS_TASKS_TEMPLATES"
    PATHS_SYSTEM_TEMPLATES = "PATHS_SYSTEM_TEMPLATES"
    PATHS_INJECT_TEMPLATES = "PATHS_INJECT_TEMPLATES"
    PATHS_MODEL_CONFIGS = "PATHS_MODEL_CONFIGS"

    # --- New Program Settings for Thinking Logic and Output Control ---
    THINKING_MODE = "THINKING_MODE" # e.g., "spinner", "dots", "progressbar"
    PRINT_MODE = "PRINT_MODE" # e.g., "token", "line", "every_x_tokens"
    TOKENS_PER_PRINT = "TOKENS_PER_PRINT" # Integer, used with "every_x_tokens"
    ENABLE_THINKING_DISPLAY = "ENABLE_THINKING_DISPLAY" # Boolean, True to show animation
    LLM_THINKING_LOG_FILE = "LLM_THINKING_LOG_FILE" # Filename for the thinking log (e.g., "llm_thinking.log")
    # --- End New Program Settings ---


class ProgramConfig(Generic[T]):

    def __init__(self, config: dict = None) -> None:
        self.config = config
        self.logger = logging.Logger(name=__file__)

    def load_predefined_config(self):
        root: str = os.path.dirname(__file__)
        config_filename: str = os.path.join(root, "config.json")
        default_config = self.__load_to_dict(config_filename)
        # handle user overrides
        user_directory = os.environ.get("AI_ASSISTANT_DIRECTORY", None)

        if user_directory:
            user_config_filename: str = os.path.join(user_directory, "config.json")
            if not exists(path=user_config_filename):
                self.copy_templates_dir(user_dir=user_directory)
                shutil.copy(config_filename, user_config_filename)

            user_config = self.__load_to_dict(user_config_filename, user_directory)
            default_config.update(**user_config)

        self.config = default_config

    def __load_to_dict(self, filename: str, root_dir=None) -> dict:
        if not exists(path=filename):
            self.logger.level = logging.ERROR
            self.logger.error("Configuration file not found.", filename)
            return None

        if root_dir is None:
            root_dir = dirname(__file__)
        with open(filename) as f:
            text_content: str = (
                pathlib.Path(filename)
                .read_text()
                .replace("{root_dir}", root_dir)
                .replace("/", os.path.sep)
            )
            dict_data: str = json.loads(text_content)
            return dict_data

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

    def copy_templates_dir(self, user_dir=None):
        if user_dir is None:
            return

        src_dir = os.path.join(dirname(__file__), "templates")
        shutil.copytree(src_dir, user_dir, dirs_exist_ok=True)
        os.sync()

    @classmethod
    def load(self):
        program_config = ProgramConfig()
        program_config.load_predefined_config()
        ProgramConfig.current = program_config
        return program_config


    current = None

