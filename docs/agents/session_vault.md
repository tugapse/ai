## 1. Architectural Role
Provides a persistent, append-only JSONL-style journaling system for storing and retrieving historical snapshots of orchestrator states associated with specific session IDs.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `SessionVault` | Class | Manages the lifecycle of session-specific state persistence, including directory creation, state committing, and state hydration. |
| `__init__` | Method | Initializes session identity, defines storage paths via `func.get_root_directory()`, and triggers directory verification. |
| `_ensure_storage` | Method | Validates or creates the `logs/agents` directory structure. |
| `commit` | Method | Serializes `orchestrator_state` into a JSON payload, optionally applies `zliz` compression and `base64` encoding, and appends the record to the session file. |
| `hydrate` | Method | Reads a specific line index from the session file, performs conditional decompression if required, and returns the extracted state dictionary. |
| `get_history_summary` | Method | Iterates through the entire session file to compile a list of metadata (turn, timestamp, agent, iteration) for debugging. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. Receives `session_id`.
    2. Resolves `storage_dir` by joining the root directory (from `func`) with `logs/agents`.
    3. Constructs `session_path` using the `session_id`.
    4. Executes `_ensure_storage` to guarantee directory existence.
- **Data Path (Commit)**: 
    `orchestrator_state` (Dict) $\rightarrow$ `payload` (Dict with timestamp/version) $\rightarrow$ `json.dumps` (String) $\rightarrow$ [Optional: `zliz.compress` $\rightarrow$ `base64.b64encode`] $\rightarrow$ Append to `session_path` (File).
- **Data Path (Hydrate)**: 
    `turn_index` (Int) $\rightarrow$ File Read $\rightarrow$ `json.loads` (Dict) $\rightarrow$ [Conditional: `base64.b64decode` $\rightarrow$ `zliz.decompress` $\rightarrow$ `json.loads`] $\rightarrow$ `state` (Dict).
- **Conditional Branching**:
    - **Storage Check**: If `storage_dir` does not exist, create it; otherwise, log verification.
    - **Compression Logic**: In `commit`, if `compress` is `True`, wrap data in a compressed payload structure; otherwise, write raw JSON.
    - **Decompression Logic**: In `hydrate`, if the entry contains `"compressed": True`, execute the decompression pipeline; otherwise, extract `"state"` directly.
    - **File Existence**: In `hydrate`, if `session_path` is missing, return `None`.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `json`, `zlib`, `base64`, `datetime`, `typing`
- **Internal Modules**: `functions` (aliased as `func`)

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `version`: `"1.0"`
    - `storage_subdir`: `"logs/agents"`
- **Environment Lookups**: 
    - `func.get_root_directory()` (Used to resolve absolute paths for storage).