## 1. Architectural Role
Provides a centralized, singleton-patterned configuration management system for handling application settings, directory structures, and template deployment via JSON persistence.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ProgramSetting` | Class | Acts as a namespace for constant string keys used to access configuration parameters. |
| `ProgramConfig` | Class | Manages the lifecycle of configuration including loading, directory provisioning, template copying, and key-value persistence. |
| `load_predefined_config` | Method | Orchestrates the setup of the user directory, template migration, and path initialization. |
| `_ensure_user_settings` | Method | Applies default values to missing keys in the configuration dictionary. |
| `save` | Method | Serializes the current configuration dictionary to a JSON file. |
| `copy_templates_to_user_dir` | Method | Recursively migrates assets from the project's `assets/templates` directory to the user's local directory. |
| `_ensure_path` | Method | Automatically generates subdirectories within the root directory if specific path settings are unset. |
| `__load_to_dict` | Method | Reads a JSON file and performs string interpolation on the `<root_dir>` placeholder. |
| `get` | Method | Retrieves a value by key with support for a default fallback. |
| `set` | Method | Updates or creates a key-value pair in the configuration. |
| `load` | ClassMethod | Initializes a `ProgramConfig` instance and assigns it to the `current` singleton reference. |

## 3. Execution Logic & Flow
- **Initialization**: 
    - `ProgramConfig.__init__` initializes an empty dictionary and a `logging.Logger` instance.
    - `ProgramConfig.load` creates the instance and triggers `load_predefined_config`.
- **Data Path**: 
    - **Input**: Environment variables (`AI_ASSISTAN_DIRECTORY`) and local `config.json`.
    - **Processing**: 
        1. Resolve user directory $\rightarrow$ 2. Check for existence/overwrite flag $\rightarrow$ 3. Copy templates if required $\rightarrow$ 4. Read and interpolate `<root_dir>` in JSON $\rightarrow$ 5. Inject default paths and user settings $\rightarrow$ 6. Verify directory existence on disk.
    - **Output**: A populated `self.config` dictionary and a synchronized filesystem state.
- **Conditional Branching**:
    - `if not exists(path=user_config_filename) or need_save`: Determines if template migration and config overwriting are required.
    - `if os.path.isdir(src_item_path)` vs `elif os.path.isfile(src_item_path)`: Dictates whether to use `shutil.copytree` or `shutil.copy2` during template deployment.
    - `if self.config.get(key) is None`: Checks for missing keys to apply default logic in `_ensure_user_settings` and `_ensure_path`.

## 4. Resource Dependencies
- **Standard Libraries**: `json`, `logging`, `os`, `shutil`, `pathlib`, `typing`
- **Internal Modules**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `ProgramSetting` keys (e.g., `MODEL_NAME`, `PATHS_LOGS`, `OLLAMA_HOST`).
    - Default `PRINT_MODE` value: `"token"`.
    - Template source path: `../../assets/templates`.
- **Environment Lookups**: 
    - `AI_ASSISTAN_DIRECTORY`: Used to define the primary user configuration root.