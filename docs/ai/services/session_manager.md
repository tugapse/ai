## Module Purpose
This module defines the `SessionManager` class, which is responsible for generating and managing session-specific file paths and directories for chat logs, thinking logs, and a workspace for generated files.

## Interface & Exports
*   `SessionManager` (Class): Manages the creation and organization of session-specific file system resources.
    *   `initialize_session_paths(config: ProgramConfig) -> Dict[str, str]`: Static method that generates and ensures the existence of all necessary directories and file paths for a new session, returning a dictionary of these paths.

## Internal Logic
The `initialize_session_paths` method performs the following steps:
1.  Generates a unique `session_timestamp` using the current date and time.
2.  Initializes a dictionary `session_paths` with placeholder values.
3.  **Chat Log Setup**: Retrieves the chat log folder path from the `config`. If configured, it ensures the directory exists and constructs the `session_chat_filepath`. Otherwise, it logs a warning.
4.  **Thinking Log Setup**: Constructs a base directory for thinking logs within the general `logs` directory from the `config`. If a base logs directory is configured, it ensures the directory exists and constructs the `session_thinking_log_filepath`. Otherwise, it logs a warning.
5.  **Workspace Setup**: Retrieves the workspace base path from the `config`. If not configured, it falls back to a default "workspaces" directory within the application's root. It then constructs a session-specific workspace path (`session_workspace_path`) and ensures this directory exists.
6.  Updates global log filenames (`func.ACTIVE_LOG_FILENAME`, `func.SESSION_LOG_FILENAME`) based on the session timestamp and configuration, and initializes these log files.
7.  Returns the `session_paths` dictionary containing all generated file and directory paths.

## Dependencies
*   `os`
*   `datetime` from `datetime`
*   `Dict`, `Any` from `typing`
*   `functions as func` (internal module)
*   `ProgramConfig`, `ProgramSetting` from `config` (internal module)

## Constants & Environment
*   Hardcoded string: `"Y%m%d_%H%M%S"` (datetime format string)
*   Hardcoded string: `"thinking"` (subdirectory name for thinking logs)
*   Hardcoded string: `"workspaces"` (fallback subdirectory name for generated files)
*   Hardcoded string: `"chat_history_"` (prefix for chat history filenames)
*   Hardcoded string: `"llm_thinking_"` (prefix for thinking log filenames)
*   Hardcoded string: `"session_"` (prefix for session workspace directory names)
*   Hardcoded string: `"active_log_filename.log"` (filename for active log)
*   Hardcoded string: `"logs"` (subdirectory name within `ProgramSetting.PATHS_LOGS` for session logs)
*   `func.ACTIVE_LOG_FILENAME` (global variable, modified by this module)
*   `func.SESSION_LOG_FILENAME` (global variable, modified by this module)
*   `func.FILE_MODE_APPEND` (constant from `functions` module)
*   `ProgramSetting.PATHS_CHAT_LOG` (enum member from `config` module)
*   `ProgramSetting.PATHS_LOGS` (enum member from `config` module)
*   `ProgramSetting.PATHS_WORKSPACES` (enum member from `config` module)