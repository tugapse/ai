## 1. Architectural Role
Manages the lifecycle, persistence, and resolution of system-wide configuration settings by merging default project templates with user-specific overrides.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ProgramSetting` | Class | Namespace for configuration key constants. |
| `ProgramConfig` | Class | Generic container for loading, storing, and accessing configuration state. |
| `ProgramConfig.load()` | Class Method | Factory method that instantiates `ProgramConfig`, triggers initialization, and sets the `current` singleton. |
| `ProgramConfig.load_predefined_config()` | Method | Orchestrates the merging of default and user JSON configs and ensures directory structures exist. |
| `ProgramConfig.save()` | Method | Serializes the current `config` dictionary to a JSON file. |
| `ProgramConfig.copy_templates_to_user_dir()` | Method | Recursively copies files/folders from the project `templates` directory to the user root. |
| `ProgramConfig.get()` | Method | Retrieves a value for a given key with an optional default. |
| `ProgramConfig.set()` | Method | Updates a configuration key-value pair. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. `ProgramConfig.load()` is called.
    2. An instance is created with an empty `config` dict and a `logging.Logger` named "Config".
    3. `load_predefined_config()` is invoked.
- **Data Path**: 
    1. **Default Load**: Reads `config.json` from the script's directory $\rightarrow$ `default_config` dict.
    2. **User Directory Resolution**: Checks `AI_ASSISTANT_DIRECTORY` env var or defaults to `~/Ai`.
    3. **User Load**: Reads `config.json` from user directory $\rightarrow$ `user_config` dict.
    4. **Merge**: `default_config` is updated with `user_config` values.
    5. **Normalization**: Sets `ROOT_DIRECTORY` and `PRINT_MODE`.
    6. **Path Enforcement**: Calls `_ensure_path` for `models`, `logs`, `workspaces`, and `databases`.
    7. **Defaulting**: Assigns `default.json` to `MODEL_CONFIG_NAME` and `False` to `VOICE_ENABLED` if missing.
- **Conditional Branching**:
    - **Overwrite Logic**: If `args.overwrite_config` is true or user config is missing, the default `config.json` and `templates` folder are copied to the user directory.
    - **Path Resolution**: `_ensure_path` only sets a value if the key is currently empty/null.
    - **File Loading**: `__load_to_dict` performs a string replacement of `<root_dir>` before parsing JSON.

## 4. Resource Dependencies
- **Standard Libraries**: `json`, `logging`, `os`, `shutil`, `pathlib`, `typing`
- **Internal Modules**: None
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `PRINT_MODE`: "token"
    - `MODEL_CONFIG_NAME` default: "default.json"
    - `VOICE_ENABLED` default: `False`
    - Default User Dir: `os.path.join(os.path.expanduser("~"), "Ai")`
- **Environment Lookups**: 
    - `AI_ASSISTANT_DIRECTORY`: Custom path for user configuration and data.