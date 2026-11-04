## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **Program Configuration Manager** | [src/ai/config.py](/src/ai/config.py) |

The `src/ai/config.py` component serves as the centralized configuration authority for the entire application. It provides a structured way to manage application settings, ranging from model parameters and file paths to UI preferences and server connectivity details. By using a singleton-like pattern via `get_current()`, it ensures that all modules within the system access a consistent set of configuration values.

This component is a foundational utility that sits at the base of the application architecture. It is responsible for bootstrapping the environment by creating necessary directory structures (such as logs, workspaces, and databases), loading user-specific JSON settings, and providing fallback defaults. It acts as the source of truth for path resolution and operational modes across the system.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `ProgramSetting` | Enum | A collection of all valid configuration keys (e.g., `MODEL_NAME`, `PATHS_LOGS`, `VECTOR_DB_PATH`). |
| `ProgramConfig(Generic[T])` | Class | The main configuration management class. |
| `ProgramConfig.get_current()` | Class Method | Returns the singleton instance of the loaded `ProgramConfig`. Raises `RuntimeError` if not initialized. |
| `ProgramConfig.load(args=None)` | Class Method | The primary entry point to initialize, load, and set the global configuration instance. |
| `ProgramConfig.get(key, default=None)` | Method | Retrieves a value for a given `ProgramSetting`. Supports a default fallback. |
| `ProgramConfig.set(key, value)` | Method | Updates or sets a value for a specific `ProgramSetting`. |
| `ProgramConfig.save(filename)` | Method | Serializes the current configuration state to a JSON file. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The configuration is managed via an internal dictionary where keys are string representations of the `ProgramSetting` enum. The `load_predefined_config` method implements a hierarchy of precedence: it first identifies a root directory (via `AI_ASSISTANT_DIRECTORY` env var or a system temp path), copies default templates from the project's `assets` folder if they are missing, and then merges user-defined JSON settings over the defaults. It also supports a `<root_dir>` placeholder within JSON files for dynamic path resolution.
- **Side Effects:** 
    - **Filesystem:** Creates directories for logs, models, workspaces, and databases. Writes `config.json` and template files to the user's configuration directory.
    - **Environment:** Reads the `AI_ASSISTANT_DIRECTORY` environment variable.
- **Error Handling:** 
    - `get_current()` raises a `RuntimeError` if called before `load()`.
    - `_load_to_dict` and `save` utilize try-except blocks to catch and log JSON parsing or I/O errors via a dedicated `logging.Logger`.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- `AI_ASSISTANT_DIRECTORY`  Defines the root directory for all application-related files and configurations. If unset, defaults to a subdirectory in the system's temporary directory.

**Module Dependencies:**
- **Standard/External:** `enum`, `json`, `logging`, `os`, `tempfile`, `shutil`, `pathlib`, `typing`.
- **Internal:** No direct internal logic dependencies are imported, but this module is consumed by nearly all other components to resolve paths and settings.