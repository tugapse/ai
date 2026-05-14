## 1. Architectural Role

**Functional Mission**
The **SessionVault** class serves as the specialized persistence layer for agentic state management. Its primary mission is to provide a durable, versioned, and optionally compressed journal of the orchestrator's state, ensuring that agent sessions can be interrupted and subsequently resumed without loss of context or progress.

**System Context & Integration**
This component acts as the long-term memory interface for the agentic workflow. It sits downstream from the orchestrator, receiving state snapshots via the `commit` method to create a JSONL-style historical record. It is designed to be utilized by higher-level management modules, such as [session_manager](/docs/services/session_manager.md) or [memory_manager](/docs/agents/memory_manager.md), to facilitate session hydration (re-inflation) and historical auditing of agent turns.

## 2. Environment & Configuration

**Environment Lookups:**
- `func.get_root_directory()`  Retrieves the base filesystem path for locating the agent storage directory.

**Hardcoded Constants:**
- `version` (Default: `"1.0"`)  The schema version assigned to each persisted state payload.
- `storage_dir` (Default: `[root]/logs/agents`)  The relative path within the root directory where session JSON files are stored.

## 3. Interface & API Surface

| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `SessionVault` | Class | Orchestrates the lifecycle of session persistence, including directory management, state committing, and state hydration. |
| `__init__` | Method | Initializes the vault with a specific `session_id` and ensures the physical storage directory exists. |
| `_ensure_storage` | Method | Internal utility to verify or create the `logs/agents` directory structure. |
| `commit` | Method | Serializes the `orchestrator_state` into a JSON payload, optionally applies `zlib` compression and `base64` encoding, and appends it to the session file. |
| `hydrate` | Method | Reads a specific turn (via `turn_index`) from the session file, performs decompression if necessary, and returns the reconstructed state dictionary. |
| `get_history_summary` | Method | Parses the entire session journal to return a lightweight list of metadata (turn, timestamp, agent, iteration) for debugging purposes. |

## 4. Execution Logic & Flow

- **Initialization**:
    1. Receives `session_id`.
    2. Resolves `storage_dir` using `func.get_root_directory()`.
    3. Constructs `session_path` by appending `{session_id}.json`.
    4. Executes `_ensure_storage` to validate the filesystem path.
- **Data Path (Commit)**:
    1. **Input**: `orchestrator_state` (Dict) and `compress` (Bool).
    2. **Transformation**: 
        - Wraps state in a payload with a UTC `timestamp` and `version`.
        - If `compress=True`: Encodes data via `zlib.compress` $\rightarrow$ `base64.b64encode` $\rightarrow$ `json.dumps`.
    3. **Output**: Appends a single JSON line to the `.json` file.
- **Data Path (Hydrate)**:
    1. **Input**: `turn_index` (Int).
    2. **Processing**: 
        - Reads file lines.
        - Selects line at `turn_index`.
        - If `compressed` flag is present: `base64.b64decode` $\rightarrow$ `zlib.decompress` $\rightarrow$ `json.loads`.
    3. **Output**: Returns the `state` dictionary or `None` if failure occurs.
- **Conditional Branching**:
    - **Storage Check**: If `session_path` does not exist during `hydrate`, returns `None`.
    - **Compression Check**: During `hydrate`, branches logic based on the presence of the `"compressed"` key in the JSON entry.
    - **Error Handling**: All major operations (`commit`, `hydrate`) are wrapped in `try-except` blocks that log errors via `func.error` rather than raising exceptions to the caller.

## 5. Resource Dependencies

- **Standard Libraries**: `os`, `json`, `zlib`, `base64`, `datetime`, `typing`
- **Internal Modules**: 
    - [functions](/docs/functions.md)
- **External Packages**: None identified.