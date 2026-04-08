## Module Purpose
This file defines classes for managing application configuration, including loading settings from default and user-specific JSON files, setting up default paths, and copying templates to a user directory. It provides a centralized way to access and persist program settings.

## Interface & Exports
*   Class: `ProgramSetting` - A class containing string constants for all configurable program settings keys.
*   Class: `ProgramConfig` - The main class for loading, managing, and saving program configuration.
*   Class Method: `ProgramConfig.load()` - A factory method to create and initialize a `ProgramConfig` instance with predefined settings.

## Internal Logic
The `ProgramConfig` class manages configuration through its `config` dictionary. The `load_predefined_config` method is central to its operation: it first loads a default `config.json` from the module's directory. It then determines a user-specific root directory, defaulting to `~/Ai` or using the `AI_ASSISTANT_DIRECTORY` environment variable, ensuring this directory exists. If a `config.json` or templates are not present in the user directory, it copies them from the project's default locations. It then loads the user's `config.json` and merges it with the default settings, prioritizing user-defined values. The method also sets various derived paths (e.g., `PATHS_LOGS`, `PATHS_MODEL_CONFIGS`, template paths) relative to the user's root directory if they are not explicitly defined. Finally, it applies default values for various program settings if they are missing and saves the consolidated configuration to the user's `config.json`. The `__load_to_dict` helper handles reading JSON files, performing path normalization, and error handling. `get` and `set` methods provide access to configuration values, and `save_config` persists the current configuration.

## Dependencies
*   `json`
*   `logging`
*   `os`
*   `os.path`
*   `shutil`
*   `pathlib`
*   `typing`

## Constants & Environment
*   **Hardcoded Settings / Global Constants**:
    *   `ProgramSetting.MODEL_NAME`
    *   `ProgramSetting.SYSTEM_PROMPT_FILE`
    *   `ProgramSetting.SYSTEM_PROMPT_FOLDER`
    *   `ProgramSetting.PATHS`
    *   `ProgramSetting.USER_PATHS`
    *   `ProgramSetting.CHAT_LOG`
    *   `ProgramSetting.TASKS_TEMPLATES`
    *   `ProgramSetting.SYSTEM_TEMPLATES`
    *   `ProgramSetting.INJECT_TEMPLATES`
    *   `ProgramSetting.OLLAMA_HOST`
    *   `ProgramSetting.PRINT_LOG`
    *   `ProgramSetting.PRINT_