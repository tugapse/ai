## 1. Architectural Role
The `ContextFile` class serves as a specialized data ingestion component responsible for the lifecycle management of external file content within the system's context. It provides a controlled mechanism to transition raw file data from the filesystem into a string-based memory state, handling existence validation and error propagation policies to support downstream processes such as [agents/context_sentinel](agents/context_sentinel.md).

## 2. Environment & Configuration
**Environment Lookups:**
No environment lookups identified.

**Hardcoded Constants:**
- `THROW_ERROR_ON_LOAD_CONTEXT_FILE_NOT_EXIST` (Default: `False`)  Global toggle determining if missing files should trigger a `FileNotFoundError`.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ContextFile` | Class | Encapsulates file path, content state, and loading logic. |
| `__init__` | Method | Configures file path and error-handling behavior. |
| `load` | Method | Executes filesystem I/O to populate `content` and update `loaded` status. |

## 4. Execution Logic & Flow
- **Initialization**: 
    - Sets `self.filename` from input.
    - Sets `self.content` to `None`.
    - Sets `self.loaded` to `False`.
    - Sets `self.throw_error_on_load` via parameter or global constant.
    - Initializes an internal `_logger`.
- **Data Path**: 
    - `filename` (str) $\rightarrow$ `Path` object $\rightarrow$ `read_text()` $\rightarrow$ `self.content` (str).
- **Conditional Branching**:
    - **File Existence Check**:
        - If `file_path.exists()` is `False`:
            - Logs error.
            - If `throw_error_on_load` is `True` $\rightarrow$ Raises `FileNotFoundError`.
            - Else $\rightarrow$ Sets `self.loaded` to `False`.
        - If `file_path.exists()` is `True`:
            - Reads text into `self.content`.
            - Sets `self.loaded` to `True`.

## 5. Resource Dependencies
- **Standard Libraries**: `logging`, `os.path`, `pathlib`
- **Internal Modules**: 
    - [core/context_file.md](core/context_file.md)
- **External Packages**: None