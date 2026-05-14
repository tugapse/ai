## 1. Architectural Role
The `SessionManager` class serves as the persistent storage abstraction layer for conversational state, responsible for the lifecycle management of JSON-based session files. It enforces filesystem security via path resolution to prevent directory traversal and provides a standardized API for CRUD operations (Create, Read, Update, Delete) on session metadata and content. This component is a critical dependency for maintaining continuity within the [modules/server/services/chat.md](modules/server/services/chat.md) and [agents/session_vault.md](agents/session_vault.md) workflows.

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `encoding="utf-8"` (Default: `"utf-8"`)  Ensures consistent character encoding for JSON I/O.
- `indent=4` (Default: `4`)  Standardizes JSON formatting for human-readability in session files.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `SessionError` | Class | Base exception for all session-related failures. |
| `SessionNotFoundError` | Class | Raised when a target `.json` session file is missing. |
| `InvalidPathError` | Class | Raised when a path attempts to escape the `root_dir`. |
| `SessionAccessError` | Class | Raised during OS-level I/O or permission failures. |
| `SessionManager` | Class | Primary controller for session filesystem operations. |
| `_log` | Method | Internal utility for optional telemetry/debug logging. |
| `_resolve_session_path`| Method | Validates and converts relative strings to absolute, secured `.json` paths. |
| `list_sessions` | Method | Scans `root_dir` for `.json` files and returns metadata sorted by mtime. |
| `load_session` | Method | Reads and parses a specific session's full JSON content. |
| `save_session` | Method | Writes new session data to a file, creating parent directories if needed. |
| `update_session_content`| Method | Overwrites the existing JSON payload of a verified session. |
| `update_session_title` | Method | Performs a partial update to the `session_title` key within a JSON file. |
| `delete_session` | Method | Removes the specified session file from the filesystem. |

## 4. Execution Logic & Flow
- **Initialization**: Sets `self.root_dir` by resolving the provided path to an absolute location and attaches an optional `logger`.
- **Data Path (Read/List)**:
    1. **Input**: `session_path` (string) or `session_folder` (optional).
    2. **Processing**: `_resolve_session_path` validates against `root_dir` $\rightarrow$ `Path.resolve()` $\rightarrow$ Prefix check $\rightarrow$ File existence check.
    3. **Output**: Parsed `dict` or `List[Dict]` of metadata.
- **Data Path (Write/Update)**:
    1. **Input**: `session_path` and `data` (dict).
    2. **Processing**: Path validation $\rightarrow$ `Path.mkdir(parents=True)` $\rightarrow$ `json.dump()` with UTF-8 encoding.
    3. **Output**: None (void).
- **Conditional Branching**:
    - **Security Check**: If `resolved.startswith(root_dir)` is false, raises `InvalidPathError`.
    - **Corruption Handling**: If `json.load()` fails, catches `JSONDecodeError` and raises specific `SessionError` subtypes.
    - **Existence Check**: Verifies `.exists()` and `.is_file()` before attempting load/update/delete.

## 5. Resource Dependencies
- **Standard Libraries**: `pathlib`, `typing`, `json`
- **Internal Modules**: 
    - [modules/server/services/session_manager.md](modules/server/services/session_manager.md)
- **External Packages**: None