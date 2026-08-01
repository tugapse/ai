import json
import logging
import os
from os.path import exists, dirname
import shutil
import pathlib
from typing import Any, TypeVar, Generic, Optional, overload

T = TypeVar("T")


class ProgramSetting:
    MODEL_NAME = "MODEL_NAME"
    MODEL_CONFIG_NAME = "MODEL_CONFIG_NAME"
    ROOT_DIRECTORY = "ROOT_DIRECTORY"
    SYSTEM_PROMPT_FILE = "SYSTEM_PROMPT_FILE"
    SYSTEM_PROMPT_FOLDER = "SYSTEM_PROMPT_FOLDER"

    PATHS_LOGS = "PATHS_LOGS"
    PATHS_CHAT_LOG = "PATHS_CHAT_LOG"
    PATHS_TASKS_TEMPLATES = "PATHS_TASKS_TEMPLATES"
    PATHS_SYSTEM_TEMPLATES = "PATHS_SYSTEM_TEMPLATES"
    PATHS_WORKSPACES = "PATHS_WORKSPACES"
    PATHS_INJECT_TEMPLATES = "PATHS_INJECT_TEMPLATES"
    PATHS_MODEL_CONFIGS = "PATHS_MODEL_CONFIGS"

    OLLAMA_HOST = "OLLAMA_HOST"
    
    PRINT_LOG = "PRINT_LOG"
    PRINT_DEBUG = "PRINT_DEBUG"
    PRINT_OUTPUT = "PRINT_OUTPUT"

    THINKING_MODE = "THINKING_MODE"
    PRINT_MODE = "PRINT_MODE"
    TOKENS_PER_PRINT = "TOKENS_PER_PRINT"
    ENABLE_THINKING_DISPLAY = "ENABLE_THINKING_DISPLAY"

    REMOTE_MODE = "REMOTE_MODE"
    REMOTE_URL = "REMOTE_URL"

    AGENT_THOUGHT = "AGENT_THOUGHT"
    HIL_TOOLS="HIL_TOOLS"

    VOICE_ENABLED = "VOICE_ENABLED"
    VOICE_FILE = "VOICE_FILE"
    VECTOR_MEMORY_ENABLED = "VECTOR_MEMORY_ENABLED"
    VECTOR_DB_PATH = "VECTOR_DB_PATH"


class ProgramConfig(Generic[T]):
    _current: Optional["ProgramConfig"] = None

    def __init__(self, config: Optional[dict] = None) -> None:
        self.config = config if config is not None else dict()
        self.logger = logging.Logger(name="Config")

    @classmethod
    def get_current(cls) -> "ProgramConfig":
        if cls._current is None:
            raise RuntimeError("ProgramConfig not initialized. Call load() first.")
        return cls._current

    def load_predefined_config(self, args):
        default_config = {}

        user_directory = os.environ.get(
            "AI_ASSISTANT_DIRECTORY", os.path.join(os.path.expanduser("~"), "Ai")
        )
        os.makedirs(user_directory, exist_ok=True)
        user_config_filename = os.path.join(user_directory, "config.json")

        need_save = (
            args.overwrite_config if hasattr(args, "overwrite_config") else False
        )

        if not exists(path=user_config_filename) or need_save:
            self.logger.info(
                f"config.json not found in {user_directory}. Copying default config."
            )
            self.copy_templates_to_user_dir(user_directory)

        user_config = self.__load_to_dict(user_config_filename, user_directory)
        if user_config:
            default_config.update(user_config)

        self.config = default_config
        self.set(ProgramSetting.ROOT_DIRECTORY, user_directory)
        self.set(ProgramSetting.PRINT_MODE, "token")

        self._ensure_path(ProgramSetting.PATHS_MODEL_CONFIGS, "models")
        self._ensure_path(ProgramSetting.PATHS_LOGS, "logs")
        self._ensure_path(ProgramSetting.PATHS_WORKSPACES, "workspaces")
        self._ensure_path(ProgramSetting.VECTOR_DB_PATH, "databases")

        self._ensure_user_settings()

        if need_save:
            self.save(user_config_filename)

    def _ensure_user_settings(self):
        if self.config.get(ProgramSetting.MODEL_CONFIG_NAME) is None:
            self.set(ProgramSetting.MODEL_CONFIG_NAME, "default.json")

        if self.config.get(ProgramSetting.SYSTEM_PROMPT_FILE) is None:
            self.set(ProgramSetting.SYSTEM_PROMPT_FILE, "default")

        if self.config.get(ProgramSetting.VOICE_ENABLED) is None:
            self.set(ProgramSetting.VOICE_ENABLED, False)

        if self.config.get(ProgramSetting.VECTOR_MEMORY_ENABLED) is None:
            self.set(ProgramSetting.VECTOR_MEMORY_ENABLED, False)

        if self.config.get(ProgramSetting.AGENT_THOUGHT) is None:
            self.set(ProgramSetting.AGENT_THOUGHT, False)
        
        if self.config.get(ProgramSetting.HIL_TOOLS) is None:
            self.set(ProgramSetting.HIL_TOOLS, ["execute_command", "write_file", "patch_file", "delete_file"])

    def save(self, filename):
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
            self.logger.info(f"Configuration saved to {filename}")
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")

    def copy_templates_to_user_dir(self, user_dir: Optional[str] = None):
        if user_dir is None:
            self.logger.warning("User directory not specified for template copy.")
            return

        project_root_templates_dir = (
            pathlib.Path(dirname(__file__)) / ".." / ".." / "assets" / "templates"
        ).resolve()

        if not os.path.exists(project_root_templates_dir):
            self.logger.warning(
                f"Source templates directory not found: {project_root_templates_dir}. Skipping template copy."
            )
            return

        self.logger.info(
            f"Copying templates from {project_root_templates_dir} to {user_dir}"
        )

        try:
            for item_name in os.listdir(project_root_templates_dir):
                src_item_path = os.path.join(project_root_templates_dir, item_name)
                dest_item_path = os.path.join(user_dir, item_name)

                if os.path.isdir(src_item_path):
                    shutil.copytree(src_item_path, dest_item_path, dirs_exist_ok=True)
                elif os.path.isfile(src_item_path):
                    shutil.copy2(src_item_path, dest_item_path)
            self.logger.info("Templates copied successfully.")
        except Exception as e:
            self.logger.error(f"Error copying templates: {e}")

    def _ensure_path(self, setting, subfolder):
        if not self.config.get(setting):
            root = self.get(ProgramSetting.ROOT_DIRECTORY)
            self.set(setting, os.path.join(root, subfolder))

    def __load_to_dict(self, filename, root_dir=None):
        if not exists(filename):
            return None
        try:
            with open(filename, "r", encoding="utf-8") as f:
                content = f.read().replace("<root_dir>", root_dir or dirname(__file__))
                return json.loads(content)
        except:
            return None

    @overload
    def get(self, key: ProgramSetting) -> Any: ...

    @overload
    def get(self, key: ProgramSetting, default: T) -> T: ...

    def get(self, key: ProgramSetting, default: Any = None) -> Any:
        return self.config.get(str(key), default)

    def set(self, key: ProgramSetting, value: Any) -> None:
        self.config[str(key)] = value

    @classmethod
    def load(cls, args=None):
        config = cls()
        config.load_predefined_config(args)
        cls._current = config
        return config