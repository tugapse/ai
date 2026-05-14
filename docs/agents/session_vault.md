## 1. Architectural Role
`SessionVault` serves as the persistence layer for agentic state management, providing a JSONL-based journaling system for session history. It is responsible for the serialization, optional compression, and retrieval of orchestrator states, ensuring that agent sessions can be reconstructed (hydrated) across execution lifecycles. It acts as a specialized storage sink within the [agents/session_vault.md](src/ai/agents/session_vault.py) component.

## 2. Environment & Configuration
**Environment Lookups:**
- `func.get_root_directory()`  Retrieves the base filesystem path for relative path construction.

**Hardcoded Constants:**
- `version` (Default: `"1.0"`)  Schema versioning for persisted JSON payloads.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `SessionVault` | Class | Manages the lifecycle of session-specific state files. |
| `__init__` | Method | Initializes session ID, defines storage paths, and triggers directory verification. |
| `_ensure_storage` | Method | Validates or creates the `logs/agents` directory structure. |
| `commit` | Method | Serializes and appends the current orchestrator state to the session file (supports `zliz` compression). |
| `hydrate` | Method | Reconstructs a specific state entry from the journal by index, handling decompression if necessary. |
| `get_history_summary` | Method | Parses the journal to return a high-level list of turn metadata (timestamp, agent, iteration). |

## 4. Execution Logic & Flow
- **Initialization**:
    1. Receives `session_id`.
    2. Resolves `storage_dir` via `functions.get_root_directory()`.
    3. Validates existence of directory via `_ensure_storage`.
- **Data Path (Commit)**:
    1. `orchestrator_state` (Dict) $\rightarrow$ `payload` (Dict with metadata).
    2. If `compress=True`: `payload` $\rightarrow$ `json.dumps` $\rightarrow$ `zliz.compress` $\rightarrow$ `base64` $\rightarrow$ `payload` (Dict).
    3. `payload` $\rightarrow$ `json.dumps` $\rightarrow$ Append to `session_path` (File).
- **Data Path (Hydrate)**:
    1. Read file $\rightarrow$ Select line by `turn_index`.
    2. If `compressed` is `True`: `base64.decode` $\rightarrow$ `zliz.decompress` $\rightarrow$ `json.loads`.
    3. Return `state` (Dict).
- **Conditional Branching**:
    - **Storage Check**: If directory doesn't exist, create it; else, log verification.
    - **Compression Check**: If `compress` flag is set during commit, apply `zliz` encoding; otherwise, write raw JSON.
    - **Compression Check (Hydrate)**: If `entry.get("compressed")` is true, trigger decompression sequence.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `json`, `zliz`, `base64`, `datetime`, `typing`
- **Internal Modules**: 
    - [functions](functions.md)
- **External Packages**: None identified.