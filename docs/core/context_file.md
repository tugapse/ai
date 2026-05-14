## 1. Architectural Role
Provides a structured abstraction for loading and managing the textual content of a file within the system context.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `THROW_ERROR_ON_LOAD_CONTEXT_FILE_NOT_EXIST` | Constant | Global default for error handling behavior during file loading. |
| `ContextFile` | Class | Encapsulates file path, content state, and loading logic. |
| `__init__` | Method | Initializes instance state including filename, error policy, and logger. |
| `load` | Method | Executes file system I/O to populate `content` and update `loaded` status. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. Receives `filename` and `throw_error_on_load` (defaults to `THROW_ERROR_ON_LOAD_CONTEXT_FILE_NOT_EXIST`).
    2. Sets `self.content` to `None`.
    3. Sets `self.loaded` to `False`.
    4. Instantiates a `logging.Logger` instance.
- **Data Path**: 
    1. **Input**: `self.filename` (string path).
    2. **Processing**: `Path(self.filename).exists()` check $\rightarrow$ `Path(self.filename).read_text()`.
    3. **Output**: `self.content` (string) and `self.loaded` (boolean).
- **Conditional Branching**:
    - **File Existence Check**:
        - **If file does not exist**:
            - Log error via `self._logger`.
            - If `self.throw_error_on_load` is `True`: Raise `FileNotFoundError`.
            - Else: Set `self.loaded = False`.
        - **If file exists**:
            - Read file content into `self.content`.
            - Set `self.loaded = True`.

## 4. Resource Dependencies
- **Standard Libraries**: `logging`, `os.path`, `pathlib.Path`
- **Internal Modules**: None
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: `THROW_ERROR_ON_LOAD_CONTEXT_FILE_NOT_EXIST = False`
- **Environment Lookups**: None