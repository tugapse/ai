## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| main | /ai/main.md |

This component serves as the primary entry point and orchestrator for the entire JARVIS system. Its core responsibility is to bootstrap the application environment, handling crucial preliminary tasks such as dependency validation, configuration loading, and argument parsing before initiating the main operational loop. It acts as the central control plane, directing the flow between various subsystems.

Architecturally, `main.py` functions as the top-level controller. It initializes core services like [DirectoryManager](/ai/services/directory_manager.md) and [ProcessManager](/ai/services/process_manager.md). It manages the system lifecycle, including setting up signal handlers for graceful shutdown and routing execution paths based on command-line arguments, whether the system is running in a chat mode, agent mode, or maintenance mode like the server.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| get_project_version | Function | Reads the project version from `pyproject.toml`, providing a fallback if the file or version key is missing. |
| check_dependencies | Function | Performs a diagnostic boot check, exiting if core required Python modules are not found. |
| hack_warnings | Function | Suppresses library-specific noise and warnings by setting environment variables and configuring logging filters. |
| JarvisHelpFormatter | Class | Custom formatter for `argparse` to ensure help messages are displayed cleanly with aligned descriptions. |
| load_args | Function | Defines and parses all command-line flags for the JARVIS ecosystem, organizing them into logical groups. |
| _instance_mode | Function | Determines the operational state of the running instance (e.g., "server", "agent", "chat") based on parsed arguments. |
| run | Function | The main execution function. It orchestrates dependency checks, config loading, and calls the main program loop. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The `run` function executes a sequential initialization pipeline: dependency check $\rightarrow$ warning suppression $\rightarrow$ configuration loading $\rightarrow$ argument processing $\rightarrow$ mode-specific execution (maintenance/server exit or main loop start). Signal handlers are registered to ensure a controlled shutdown upon interruption.
- **Side Effects:** Reads and writes to the filesystem (to find `pyproject.toml`), interacts with the terminal/console (printing status messages, logos, and errors), and spawns/manages internal processes via [ProcessManager](/ai/services/process_manager.md).
- **Error Handling:** Uses a broad `try...except` block in `run()` to catch operational exceptions, logging them gracefully if the `--debug-console` flag is active, or displaying a generic error otherwise. Fallback versions are used in `get_project_version` upon file access errors.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `os`, `sys`, `importlib.util`, `argparse`, `warnings`, `logging`, `traceback`, `time`, `signal`, `gc`, `re`, `pathlib`.
- **Internal:** [DirectoryManager](/ai/services/directory_manager.md), [ProcessManager](/ai/services/process_manager.md), [ProgramConfig](/ai/config.md), [ProgramSetting](/ai/config.md), [ModelType](/ai/entities/model_enums.md), [ai.functions](/ai/functions.md), [ai.color](/ai/color.md), [ai.program](/ai/program.md), [ai.cli_args](/ai/cli_args.md).