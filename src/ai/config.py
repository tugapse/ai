from enum import Enum
import json
import logging
import os
import tempfile
from os.path import exists, dirname
import shutil
import pathlib
from typing import Any, TypeVar, Generic, Optional, overload

T = TypeVar("T")


class ProgramSetting(Enum):
    """
    Defines all possible configuration keys used throughout the program.
    Each member represents a specific setting that can be loaded or saved.
    """
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
    # Built-in tool modules (enabled when the key is absent)
    TOOLS_FILESYSTEM_ENABLED = "TOOLS_FILESYSTEM_ENABLED"
    TOOLS_SEARCH_ENABLED = "TOOLS_SEARCH_ENABLED"
    TOOLS_SHELL_ENABLED = "TOOLS_SHELL_ENABLED"
    TOOLS_WEB_ENABLED = "TOOLS_WEB_ENABLED"
    TOOLS_NOTIFY_ENABLED = "TOOLS_NOTIFY_ENABLED"
    VECTOR_DB_PATH = "VECTOR_DB_PATH"
    VECTOR_RECENCY_WEIGHT = "VECTOR_RECENCY_WEIGHT"
    VECTOR_IMPORTANCE_WEIGHT = "VECTOR_IMPORTANCE_WEIGHT"
    VECTOR_RELEVANCE_WEIGHT = "VECTOR_RELEVANCE_WEIGHT"
    SERVER_HOST = "SERVER_HOST"    
    SERVER_PORT = "SERVER_PORT"
    SERVER_TRUSTED_NETWORKS = "SERVER_TRUSTED_NETWORKS"  # CIDRs allowed on protected routes (default LAN + Tailscale)
    SERVER_ALLOWED_ORIGINS = "SERVER_ALLOWED_ORIGINS"    # Browser origins allowed by CORS (default localhost:4200)
    SERVER_TOTP_TOOLS = "SERVER_TOTP_TOOLS"              # Tools whose approval needs an authenticator code
    SERVER_AGENT_WORKDIR = "SERVER_AGENT_WORKDIR"  # Folder web agent runs work in (default ~/Ai/workspace)

    def __str__(self) -> str:
        """Returns the string value associated with the enum member."""
        return self.value
    
    def __repr__(self) -> str:
        """Returns a developer-friendly representation of the enum member."""
        return f"ProgramSetting.{self.name}"


class ProgramConfig(Generic[T]):
    """
    Manages the application's configuration settings.

    This class handles loading configurations from user-specific JSON files,
    setting defaults, ensuring necessary directory structures exist, and
    providing a centralized way to access configuration values via ProgramSetting enums.
    """
    _current: Optional["ProgramConfig"] = None

    def __init__(self, config: Optional[dict] = None) -> None:
        """
        Initializes the configuration object.

        Args:
            config: An optional dictionary containing initial configuration values.
        """
        self.config = config if config is not None else dict()
        self.logger = logging.Logger(name="Config")

    @classmethod
    def get_current(cls) -> "ProgramConfig":
        """
        Retrieves the currently loaded configuration instance.

        Returns:
            ProgramConfig: The initialized configuration object.

        Raises:
            RuntimeError: If ProgramConfig has not been initialized via load().
        """
        if cls._current is None:
            raise RuntimeError("ProgramConfig not initialized. Call load() first.")
        return cls._current

    def load_predefined_config(self, args) -> None:
        """
        Loads the configuration, prioritizing user settings over defaults.

        It determines the user's configuration directory, copies default templates
        if necessary, loads existing user settings, and sets up required paths.

        Args:
            args: An object containing command-line arguments, expected to have 
                  an 'overwrite_config' attribute.
        """
        default_config = {}

        default_root = os.environ.get("AI_ASSISTANT_DIRECTORY")
        if not default_root:
            default_root = os.path.join(tempfile.gettempdir(), "ai")
        user_directory = os.path.abspath(default_root)
        os.makedirs(user_directory, exist_ok=True)
        user_config_filename = os.path.join(user_directory, "config.json")

        need_save = args.overwrite_config if hasattr(args, "overwrite_config") else False
        

        if not exists(path=user_config_filename) or need_save:
            need_save = True
            self.logger.info(
                f"Copying default config."
            )
            self.copy_templates_to_user_dir(user_directory)

        user_config = self.__load_to_dict(user_config_filename, user_directory)
        if user_config and not need_save:
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

    def _ensure_user_settings(self) -> None:
        """
        Ensures that essential user settings have default values if they are missing.
        """
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

    def save(self, filename: str) -> None:
        """
        Saves the current configuration dictionary to the specified JSON file.

        Args:
            filename: The full path to the configuration file to save to.
        """
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
            self.logger.info(f"Configuration saved to {filename}")
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
    
    def copy_skip_existing(self, src: str, dst: str, *, follow_symlinks: bool = True) -> str:
        """
        Copies a file from source to destination, skipping the copy if the destination already exists.

        Args:
            src: The source file path.
            dst: The destination file path.
            follow_symlinks: Whether to follow symbolic links during the copy.

        Returns:
            str: The destination path.
        """
        if os.path.exists(dst):
            return dst
        return shutil.copy2(src, dst, follow_symlinks=follow_symlinks)

    
    def copy_templates_to_user_dir(self, user_dir: Optional[str] = None) -> None:
        """
        Copies template directories and files from the application's asset folder
        to the user's configuration directory.

        Args:
            user_dir: The target directory where templates should be copied.
        """
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
                    shutil.copytree(src_item_path, dest_item_path, dirs_exist_ok=True,copy_function=self.copy_skip_existing )
                    
                elif os.path.isfile(src_item_path) and not os.path.exists(dest_item_path):
                    shutil.copy2(src_item_path, dest_item_path)

            self.logger.info("Templates copied successfully.")
        except Exception as e:
            self.logger.error(f"Error copying templates: {e}")

    def _ensure_path(self, setting: ProgramSetting, subfolder: str) -> None:
        """
        Ensures a specific path exists within the root directory and sets the corresponding
        configuration setting if it is currently unset.

        Args:
            setting: The ProgramSetting enum key to update (e.g., PATHS_LOGS).
            subfolder: The name of the subdirectory to create (e.g., "logs").
        """
        if not self.config.get(setting):
            root = self.get(ProgramSetting.ROOT_DIRECTORY)
            self.set(setting, os.path.join(root, subfolder))

    def __load_to_dict(self, filename: str, root_dir: Optional[str] = None) -> Optional[dict]:
        """
        Loads configuration data from a JSON file.

        It handles potential placeholders like <root_dir> within the file content.

        Args:
            filename: The path to the JSON configuration file.
            root_dir: An optional directory path to substitute for <root_dir> placeholders.

        Returns:
            Optional[dict]: The loaded configuration dictionary, or None if loading fails.
        """
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
        """
        Retrieves a configuration value based on the provided ProgramSetting key.

        Args:
            key: The ProgramSetting enum identifying the configuration item.
            default: The value to return if the key is not found in the configuration.

        Returns:
            Any: The stored configuration value or the provided default.
        """
        return self.config.get(str(key), default)

    def set(self, key: ProgramSetting, value: Any) -> None:
        """
        Sets or updates a configuration value in the internal configuration dictionary.

        Args:
            key: The ProgramSetting enum identifying the configuration item.
            value: The new value to assign to the setting.
        """
        self.config[str(key)] = value

    @classmethod
    def load(cls, args=None) -> "ProgramConfig":
        """
        The primary entry point for configuration loading.

        Initializes a ProgramConfig instance, loads defaults and user settings,
        and sets the instance as the current global configuration.

        Args:
            args: Optional arguments object used to determine if configuration should be overwritten.

        Returns:
            ProgramConfig: The fully loaded and initialized configuration object.
        """
        config = cls()
        config.load_predefined_config(args)
        cls._current = config
        return config