## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **Program Configuration Engine** | [src/ai/config.py](/AgentDocs/ai/config.md) |

The `src/ai/config.py` component provides a centralized, singleton-pattern configuration management system for the entire application. It is responsible for defining all valid configuration keys via the `ProgramSetting` enumeration and managing the lifecycle of application settings, including loading from disk, applying defaults, and ensuring the necessary directory structures exist on the host filesystem.

In the broader system architecture, this component serves as a foundational utility used by almost all other modules to resolve paths (such as logs, workspaces, and model configurations) and to toggle feature flags (such as voice enablement or vector memory). It acts as the single source of truth for environmental settings, bridging the gap between command-line arguments, environment variables, and persistent JSON storage.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `ProgramSetting` | Enum | A collection of all valid configuration keys used by the system (e.g., `MODEL_NAME`, `PATHS_LOGS`, `VECTOR_DB_PATH`). |
| `ProgramConfig[T]` | Class | The primary configuration manager. Implements a singleton pattern via `get_current()`. |
| `ProgramConfig.load(args=None)` | Class Method | The primary entry point to initialize the configuration, load user settings, and set the global instance. |
| `ProgramConfig.get_current()` | Class Method | Returns the active `ProgramConfig` instance. Raises `RuntimeError` if called before `load()`. |
| `ProgramConfig.get(key, default=None)` | Method | Retrieves a value for a given `ProgramSetting`. Supports type-hinted overloads for default values. |
| `ProgramConfig.set(key, value)` | Method | Updates or creates a configuration entry for a given `ProgramSetting`. |
| `ProgramConfig.save(filename)` | Method | Persists the current in-memory configuration to a JSON file. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The component uses a dictionary-based storage mechanism where keys are cast to strings from the `ProgramSetting` enum. It implements a hierarchical loading strategy: it first determines a root directory (via `AI_ASSISTANT_DIRECTORY` env var or a temp directory), copies default template assets from the project's `assets/templates` folder if they are missing, and then merges user-defined JSON settings with hardcoded defaults. It also supports a `<root_dir>` placeholder within JSON files for dynamic path resolution.
- **Side Effects:** 
    - **Filesystem:** Creates directories for logs, workspaces, models, and databases. Writes `config.json` and copies template files to the user's configuration directory.
    - **Environment:** Reads from `os.environ` to locate the application root.
- **Error Handling:** 
    - `get_current()` raises a `RuntimeError` if the configuration hasn't been initialized.
    - `_load_to_dict` and `save` utilize try-except blocks to catch and log I/O or JSON parsing errors via a dedicated `logging.Logger`.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- `AI_ASSISTANT_DIRECTORY`  Defines the absolute path for the user's configuration and data directory. If unset, defaults to a subdirectory in the system's temporary directory.

**Module Dependencies:**
- **Standard/External:** `enum`, `json`, `logging`, `os`, `tempfile`, `shutil`, `pathlib`, `typing`.
- **Internal:** No direct internal logic dependencies are imported, though it provides the configuration used by components like [src/ai/program.md](/AgentDocs/ai/program.md) and [src/ai/model_config_manager.py](/AgentDocs/ai/model_config_manager.md).