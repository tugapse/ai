## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| AgentSessionManager | ai/agents/session_manager |

This component is responsible for the persistence layer of agent sessions. Its primary duty is to manage the lifecycle of a single agent's interaction history, ensuring that the state—including conversation turns, memory, and iteration counts—can be reliably saved and reloaded across multiple executions. It achieves this by creating a structured directory based on the working directory's hash and storing state updates in a journal file.

Architecturally, `AgentSessionManager` functions as a critical service layer component, sitting between the agent logic and the persistent storage system. It relies on [DirectoryManager](/ai/services/directory_manager.md) to locate system directories and utilizes file I/O to manage the session journal and associated metadata manifests.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| `AgentSessionManager` | Class | Manages persistence for agent sessions. Initializes storage based on session ID and working directory. |
| `AgentSessionManager.get_agents_storage_root` | Method | Retrieves the absolute path to the root directory for all agent session data. |
| `AgentSessionManager.__init__` | Method | Initializes the manager, calculating storage paths based on session and working directory hashes, and ensures storage exists. |
| `AgentSessionManager.commit` | Method | Persists the current orchestrator state to the session's journal file, supporting optional compression. |
| `AgentSessionManager.get_session` | Method | Hydrates the orchestrator state from the session file at a specified turn index. |
| `AgentSessionManager.get_working_directory_for_hash` | Method | Resolves the original working directory path given a 16-character hash code. |
| `AgentSessionManager.list_all_projects` | Method | Returns a list of all tracked projects, mapping their hash to their original working directory. |
| `AgentSessionManager.list_sessions` | Method | Lists all sessions within a given working directory, attempting to extract the initial user request from the first journal entry. |
| `AgentSessionManager.list_sessions_detailed` | Method | Lists sessions for a directory, providing detailed metadata like last update time, turn count, and user request. |
| `AgentSessionManager.extract_transcript` | Method | Rebuilds a visible conversation transcript from a loaded session state, limited by a specified count. |
| `AgentSessionManager.get_history_summary` | Method | Reads the entire session journal to return a turn-by-turn summary of the session's key metadata. |
| `AgentSessionManager._extract_user_request_from_entry` | Method | Extracts the initial user request string from a complex session state entry by searching common state fields. |
| `AgentSessionManager._read_entry_state` | Method | Decodes a single journal line, handling both plain and compressed (zlib/base64) entries. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The core logic revolves around path construction using SHA256 hashes of working directories to namespace sessions (`system/logs/agents/<hash>/<session_id>.json`). State persistence involves appending JSON objects to a file, which can be optionally compressed using `zlib` and encoded using `base64` before writing. Retrieval involves reading line-by-line and conditionally decompressing data based on metadata flags.
- **Side Effects:** The component has extensive filesystem side effects, including creating directories (`os.makedirs`), reading (`open(..., "r")`), and writing (`open(..., "a")`) to the persistent storage location.
- **Error Handling:** Robust error handling is present across all I/O operations. `try...except` blocks catch `OSError` during file operations and `json.JSONDecodeError` during parsing, logging errors via `func.error` instead of crashing the process.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `os`, `json`, `zlib`, `base64`, `hashlib`, `datetime`, `typing`.
- **Internal:** [ai.functions](/ai/functions.md), [ai.services.directory_manager](/ai/services/directory_manager.md).