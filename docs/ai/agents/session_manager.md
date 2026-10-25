## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | AgentSessionManager |
| Source file | session_manager.py |

The **AgentSessionManager** serves as the persistence layer for agentic workflows, providing a structured mechanism to journal the state of an orchestrator over time. It implements a content-addressable storage pattern by hashing the working directory to create isolated, collision-resistant storage silos for different projects.

**Functional Mission**
The primary responsibility of **AgentSessionManager** is to ensure the durability and recoverability of agent sessions. It solves the problem of state loss during long-running or interrupted agent executions by implementing a JSON-based journaling system that supports both plain-text and compressed (zlib/base64) state snapshots.

**System Context & Integration**
This component acts as a bridge between the volatile runtime state of an agent and the physical filesystem. It is designed to be utilized by orchestration layers to "checkpoint" progress. Downstream, it enables session re-inflation (hydration), allowing an agent to resume from a specific turn index. It interacts heavily with [ai.functions](/docs/ai/functions.md) for logging and debugging, and its data structures are intended to be consumed by higher-level services like [session_manager](/docs/ai/services/session_manager.md) or API endpoints such as [sessions](/docs/ai/modules/server/routers/sessions.md).

## 2. Environment & Configuration
**Environment Lookups:**
- `working_directory` (via `__init__`)  Determines the root context for hashing and storage path generation.

**Hardcoded Constants:**
- `MANIFEST_FILE` (Default: `"manifest.json"`)  The filename used to store directory-level metadata.
- `version` (Default: `"1.0"`)  The schema version embedded in every committed state payload.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `AgentSessionManager` | Class | Orchestrates session lifecycle, including creation, commitment, and hydration. |
| `__init__` | Method | Initializes directory hashing, storage paths, and ensures manifest existence. |
| `_ensure_storage` | Method | Creates the physical directory structure and writes the `manifest.json` if missing. |
| `commit` | Method | Appends a timestamped state snapshot to the session journal (supports optional compression). |
| `get_session` | Method | Retrieves and de-serializes a specific state entry from the journal by index. |
| `get_working_directory_for_hash` | Static Method | Resolves a directory path using a provided hash via the manifest file. |
| `list_all_projects` | Static Method | Scans the agent storage root to return all tracked project hashes and paths. |
| `_extract_user_request_from_entry` | Static Method | Heuristically parses a state entry to find the original user prompt/request. |
| `list_sessions` | Static Method | Lists all available session IDs and their associated user requests for a specific directory. |
| `get_history_summary` | Method | Generates a lightweight metadata list of all turns (timestamp, agent, iteration) for debugging. |

## 4. Execution Logic & Flow
- **Initialization**: 
    1. Normalize the `working_directory`.
    2. Generate a 16-character SHA-256 prefix (`parent_dir`) from the directory path.
    3. Construct `storage_dir` (relative to `logs/agents/`) and `session_path`.
    4. Trigger `_ensure_storage` to create directories and the `manifest.json` containing the original path and creation timestamp.
- **Data Path (Commitment)**: 
    `orchestrator_state` (Dict) $\rightarrow$ `json.dumps` $\rightarrow$ (Optional: `zlib.compress` + `base64.b64encode`) $\rightarrow$ Append to `session_path` with newline.
- **Data Path (Hydration)**: 
    `turn_index` $\rightarrow$ Read line from `session_path` $\rightarrow$ `json.loads` $\rightarrow$ (If compressed: `base64.b64decode` $\rightarrow$ `zlib.decompress`) $\rightarrow$ `state` (Dict).
- **Conditional Branching**:
    - **Compression Check**: During `get_session`, the logic checks the `compressed` boolean key to decide whether to trigger the decompression pipeline.
    - **Manifest Existence**: During `_ensure_storage`, the system checks for `manifest.json` to prevent overwriting existing project metadata.
    - **Request Extraction**: `_extract_user_request_from_entry` uses a multi-tiered fallback strategy (direct keys $\rightarrow$ nested agent/memory containers $\rightarrow$ history sequences) to locate user input.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `json`, `zlib`, `base64`, `hashlib`, `datetime`, `typing`
- **Internal Modules**: 
    - [ai.functions](/docs/ai/functions.md)
- **External Packages**: None identified.