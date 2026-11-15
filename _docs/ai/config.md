## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| ProgramConfig | /ai/config.md |

This component is responsible for managing the entire application configuration state. It defines a centralized system, using the `ProgramSetting` Enum, to provide strongly-typed access to all configuration parameters, ranging from model names and logging paths to complex server settings and tool enablement flags. Its primary responsibility is to ensure that configuration values are loaded correctly, either from user-specific JSON files or from predefined system defaults.

The `ProgramConfig` class acts as the core configuration service layer for the application. It orchestrates the loading process by reading user settings, ensuring necessary directories exist (like paths for logs or workspaces), and applying sensible defaults for missing keys. It serves as the authoritative source of truth for runtime parameters used across other services, such as the [ai/agent.md] or [ai/server.md].

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| ProgramSetting | Enum | Defines all possible configuration keys used throughout the program. |
| ProgramConfig | Class | Manages the application's configuration settings, handling loading and retrieval. |
| get | Method | Retrieves a configuration value based on the provided ProgramSetting key, with an optional default. |
| set | Method | Sets or updates a configuration value in the internal configuration dictionary. |
| load | Class Method | The primary entry point for configuration loading, initializing and returning the global configuration instance. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The configuration loading process (`load_predefined_config`) first determines the user's configuration directory based on environment variables or a default temp location. It then checks for an existing configuration file. If the file is missing or the user requests an overwrite, it copies default templates from the application's asset folder. Finally, it merges user settings with hardcoded defaults and ensures critical subdirectories (like `logs` or `databases`) exist within the root path.
- **Side Effects:** Reads and writes to the filesystem (reading/writing `config.json`, copying template directories). It also utilizes Python's `logging` module to record operations.
- **Error Handling:** Catches general exceptions during file saving and template copying, logging them as errors rather than halting execution. The `get` method allows for graceful fallback using a provided default value.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- AI_ASSISTANT_DIRECTORY — Specifies the base directory where user configuration files should reside. Defaults to a directory in the system's temporary folder.

**Module Dependencies:**
- **Standard/External:** `enum`, `json`, `logging`, `os`, `tempfile`, `shutil`, `pathlib`, `typing`.
- **Internal:** None.