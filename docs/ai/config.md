## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | ProgramConfig |
| Source file | config.py |

The **ProgramConfig** component serves as the centralized configuration authority for the entire AI assistant ecosystem. It manages the lifecycle of application settings, ranging from model parameters and directory structures to feature toggles like voice enablement and vector memory. By providing a unified interface for retrieving and updating settings, it ensures consistency across all modules.

**Functional Mission**
The primary responsibility of **ProgramConfig** is to provide a robust, singleton-patterned configuration management system. It solves the problem of fragmented state by consolidating environment lookups, file-based persistence (JSON), and default template provisioning into a single source of truth. Its core mission is to ensure that the application environment is correctly initialized, directory structures are present, and settings are accessible via type-safe enums.

**System Context & Integration**
This component acts as a foundational utility used by nearly every high-level module. It is responsible for setting the `ROOT_DIRECTORY`, which dictates the pathing for all other components. It integrates with the filesystem to bootstrap the user's environment by copying assets from the project's template directory to a user-specific directory. Downstream modules, such as [Model Orchestrator](/docs/ai/services/model_orchestrator.md) or [Vector Memory Module](/docs/ai/modules/vector_memory/vector_memory_module.md), rely on this component to resolve paths for model configurations, databases, and logs.

- **INTERNAL REFERENCES**: [ProgramConfig](/docs/ai/config.md)

## 2. Environment & Configuration
**Environment Lookups:**
- `AI_ASSISTANT_DIRECTORY` (via `load_predefined_config`)  Determines the base directory for user configurations and assets; defaults to `~/Ai`.

**Hardcoded Constants:**
- `MODEL_CONFIG_NAME` (Default: `"default.json"`)  The filename for the active model configuration.
- `SYSTEM_PROMPT_FILE` (Default: `"default"`)  The base name for the system prompt file.
- `VOICE_ENABLED` (Default: `False`)  Toggle for voice capabilities.
- `VECTOR_MEMORY_ENABLED` (Default: `False`)  Toggle for RAG/Vector database features.
- `AGENT_THOUGHT` (Default: `False`)  Toggle for displaying agent reasoning.
- `HIL_TOOLS` (Default: `["execute_command", "write_file", "patch_file", "delete_file"]`)  List of tools requiring Human-In-The-Loop intervention.
- `PRINT_MODE` (Default: `"token"`)  Sets the default output verbosity mode.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ProgramSetting` | Enum | Defines the strictly typed keys used for all configuration lookups. |
| `ProgramConfig` | Class | The main configuration manager implementing the Singleton pattern. |
| `load()` | Class Method | Initializes the configuration instance and sets the global `_current` state. |
| `get()` | Method | Retrieves a value for a given `ProgramSetting`, supporting default values. |
| `set()` | Method | Updates a configuration value for a given `ProgramSetting`. |
| `save()` | Method | Persists the current configuration dictionary to a JSON file. |
| `load_predefined_config()` | Method | Orchestrates directory creation, template copying, and JSON loading. |
| `copy_templates_to_user_dir()` | Method | Migrates assets from the project's `assets/templates` to the user directory. |

## 4. Execution Logic & Flow
- **Initialization**: 
    1. `load()` is called, instantiating `ProgramConfig`.
    2. `load_predefined_config()` is invoked to determine the `user_directory`.
    3. The system checks for the existence of `config.json` in the user directory.
- **Data Path**: 
    1. **Input**: Environment variables or existing `config.json`.
    2. **Processing**: If no config exists (or `overwrite_config` is true), `copy_templates_to_user_dir` is triggered. The `__load_to_dict` method reads the JSON and performs string replacement for `<root_dir>` placeholders.
    3. **Output**: A populated `self.config` dictionary and a set of validated directory paths.
- **Conditional Branching**:
    - **Config Existence**: If `config.json` is missing, the system enters "Bootstrap Mode" (copying templates and creating a new file). If present, it enters "Load Mode".
    - **Path Validation**: `_ensure_path` checks if specific subfolders (logs, workspaces, etc.) are defined; if not, it derives them from the `ROOT_DIRECTORY`.
    - **Error Handling**: `save()` and `__load_to_dict` use try-except blocks to prevent application crashes during I/O failures, logging errors via the internal `self.logger`.

## 5. Resource Dependencies
- **Standard Libraries**: `enum`, `json`, `logging`, `os`, `shutil`, `pathlib`, `typing`
- **Internal Modules**: None identified (this is a foundational utility).
- **External Packages**: None identified.