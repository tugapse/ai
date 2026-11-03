## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **AgentSessionManager** | [src/ai/agents/session_manager.py](/AgentDocs/ai/agents/session_manager.py) |

The `AgentSessionManager` is responsible for the persistent storage and retrieval of agent session states. It provides a mechanism to journal the evolution of an orchestrator's state over time, allowing for session re-inflation (hydration) and historical auditing.

Within the broader application architecture, this component acts as a specialized persistence layer for agentic workflows. It organizes data using a hashed directory structure based on the agent's working directory to prevent collisions and manage large volumes of session logs. It ensures that every session is accompanied by a metadata manifest that tracks the originating environment.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `AgentSessionManager(session_id: str, working_directory: Optional[str] = None)` | Class | Initializes a manager for a specific session. Creates the storage directory and `manifest.json` if they do not exist. |
| `commit(orchestrator_state: Dict[str, Any], compress: bool = False)` | Method | Appends the current orchestrator state to the session's JSON journal. Supports optional `zlib` compression and `base64` encoding. |
| `get_session(turn_index: int = -1) -> Optional[Dict[str, Any]]` | Method | Retrieves a specific state entry from the journal by index. Defaults to the most recent entry (`-1`). Handles decompression automatically. |
| `get_working_directory_for_hash(hash_code: str) -> Optional[str]` | Static Method | Resolves a physical working directory path using a 16-character SHA256 hash prefix via the session manifest. |
| `list_all_projects() -> List[Dict[str, str]]` | Static Method | Scans the agents storage root and returns a list of all tracked projects, mapping hashes to their original working directories. |
| `list_sessions(working_directory: Optional[str] = None) -> list` | Static Method | Lists all session IDs and their associated initial user requests within a specific working directory's hash bucket. |
| `get_history_summary() -> list` | Method | Returns a list of metadata summaries (turn index, timestamp, agent ID, and iteration) for every entry in the session journal. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The manager uses a "journaling" approach where each state update is appended as a new line in a JSONL-style format. To optimize storage for large states, the `commit` method can compress payloads using `zlib` before `base64` encoding them into the JSON string. Directory organization is achieved by taking the first 16 characters of a SHA256 hash of the absolute working directory path.
- **Side Effects:** 
    - **Filesystem:** Creates directories and files within the system logs directory (specifically `<system>/logs/agents/[hash]/`).
    - **Filesystem:** Writes `manifest.json` for every new directory created.
    - **Filesystem:** Appends data to `.json` session files.
- **Error Handling:** The component uses broad `try-except` blocks during file I/O and JSON parsing to prevent session persistence failures from crashing the main agent loop. If a hydration or commit fails, it logs the error via `func.error` and returns `None` or fails gracefully.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No direct environment variables are consumed by this component; it relies on the `DirectoryManager` to resolve system paths.

**Module Dependencies:**
- **Standard/External:** `os`, `json`, `zlib`, `base64`, `hashlib`, `datetime`, `typing`.
- **Internal:** 
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ai.services.directory_manager](/AgentDocs/ai/services/directory_manager.md)