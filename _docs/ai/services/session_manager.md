## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| SessionManager | /ai/services/session_manager.md |

This component is responsible for managing the lifecycle and persistence of application sessions. Its primary responsibility is to generate a unique session identifier, ensuring that if the application is restarted shortly after a previous run, it attempts to resume the state of the most recent "warm" session. This persistence mechanism relies on checking the modification time of a specific ID file to determine session continuity.

The `SessionManager` functions as a core service layer component, handling initialization logic before the main application workflow begins. It coordinates with other services like [DirectoryManager](/ai/services/directory_manager.md) to correctly locate and create session-specific paths for chat logs, thinking logs, and error tracking, thereby providing a structured environment for the rest of the application logic to operate within.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| SessionManager.initialize_session_paths | Static Method | Generates and ensures existence of session-specific directories and file paths. Attempts to resume the most recent session if it's 'warm' (less than 5 minutes old). Returns a dictionary containing session identifiers and file paths. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The initialization process first checks for a persistence file (`last_session.id`). If found, it compares the file's modification time against a 5-minute threshold (300 seconds). If the session is warm, the existing ID is reused; otherwise, a new timestamped ID is generated and written to the persistence file. Session paths are then constructed using this ID, creating directories and naming files for chat history and LLM thinking logs.

- **Side Effects:** Reads from and writes to the filesystem (e.g., `last_session.id`, chat log files, thinking log files). It also mutates global state via `ai.functions` by setting `func.ACTIVE_ERROR_FILENAME`, `func.SESSION_ERROR_FILENAME`, etc.

- **Error Handling:** The component explicitly checks for the existence of directories (`func.ensure_directory_exists`) and handles the case where log paths might not be configured, logging a warning if necessary.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `os`, `time`, `datetime`, `typing`
- **Internal:** [ai.functions](/ai/functions.md), [ai.services.config_helper](/ai/services/config_helper.md), [ai.services.directory_manager](/ai/services/directory_manager.md)