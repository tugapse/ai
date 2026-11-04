## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **AgentSessionManager** | [src/ai/agents/session_manager.py](/src/ai/agents/session_manager.py) |

The `AgentSessionManager` is responsible for the persistent storage and retrieval of agent session states. It provides a mechanism to journal the evolution of an orchestrator's state over time, allowing for session re-inflation (hydration) and historical auditing.

This component serves as a specialized persistence layer within the agent architecture. It organizes data into a structured filesystem hierarchy based on a SHA256 hash of the agent's working directory, ensuring that session logs are logically grouped and isolated from other system logs. It utilizes a JSON-line format for the journal files, supporting optional compression for large state objects.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `AgentSessionManager(session_id: str, working_directory: Optional[str] = None)` | Class | Initializes a manager for a specific session. Sets up the storage directory and creates a `manifest.json` if necessary. |
| `commit(orchestrator_state: Dict[str, Any], compress: bool = False)` | Method | Appends the current orchestrator state to the session journal. Supports zlib compression and base64 encoding. |
| `get_session(turn_index: int = -1) -> Optional[Dict[str, Any]]` | Method | Retrieves a specific state entry from the journal by index (defaults to the most recent). Handles decompression automatically. |
| `get_working_directory_for_hash(hash_code: str) -> Optional[str]` | Static Method | Resolves the original absolute working directory path using a provided 16-character hash prefix. |
| `list_all_projects() -> List[Dict[str, str]]` | Static Method | Scans the agents storage root and returns a list of all tracked projects with their hashes and directory paths. |
| `list_sessions(working_directory: Optional[str] = None) -> list` | Static Method | Lists all session IDs and their associated initial user requests within a specific working directory context. |
| `get_history_summary() -> list` | Method | Returns a list of metadata summaries (turn, timestamp, agent, iteration) for every entry in the current session. |

## 3. Implementation Details & Side Effects
- **Core Logic:** 
    - **Storage Hierarchy:** Uses `DirectoryManager` to locate the system logs, then creates a subfolder structure: `<logs>/agents/[16_char_hash]/[session_id].json`.
    - **Journaling:** The session file is treated as a newline-delimited JSON (ndjson) file. Each "turn" is a single JSON object on a new line.
    - **Compression:** When `compress=True` is passed to `commit`, the state is serialized, compressed via `zlib`, encoded in `base64`, and wrapped in a metadata envelope.
    - **Request Extraction:** Uses a heuristic search pattern in `_extract_user_request_from_entry` to find the original user prompt by traversing common keys like `user_request`, `prompt`, or nested message histories in `agents` or `memory` containers.
- **Side Effects:** 
    - **Filesystem IO:** Creates directories via `os.makedirs` and writes/appends to files (`manifest.json` and session `.json` files).
    - **Logging:** Dispatches debug, info, and error logs via the `ai.functions` module.
- **Error Handling:** 
    - Uses broad `try-except` blocks around file operations and JSON parsing to prevent session crashes. 
    - If hydration fails or a file is missing, it returns `None` or an empty list rather than raising exceptions, ensuring the agent can attempt to "start fresh."

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No specific environment variables are required, though the base path is determined by the `DirectoryManager` implementation.

**Module Dependencies:**
- **Standard/External:** `os`, `json`, `zlib`, `base64`, `hashlib`, `datetime`, `typing`.
- **Internal:** 
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ai.services.directory_manager](/AgentDocs/ai/services/directory_manager.md)