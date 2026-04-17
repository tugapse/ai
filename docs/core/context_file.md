## 1. Architectural Role
Provides a managed wrapper for loading and storing the text content of a specific filesystem path into memory for use as system context.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ContextFile` | Class | Manages the lifecycle of a single file's content, from path definition to memory loading. |
| `ContextFile.__init__` | Method | Initializes state, sets the target filename, and configures error handling behavior. |
| `ContextFile.load` | Method | Executes the filesystem read operation and updates the `content` and `loaded` status. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. Assigns `filename` and `throw_error_on_load` (defaulting to `THROW_ERROR_ON_LOAD_CONTEXT_FILE_NOT_EXIST`).
    2. Sets `content` to `None` and `loaded` to `False`.
    3. Instantiates a `logging.Logger` tied to the current file.
- **Data Path**: `filename` (string) $\rightarrow$ `Path` object $\rightarrow$ `read_text()` $\rightarrow$ `self.content` (string).
- **Conditional Branching**:
    - **File Existence Check**: If `Path(self.filename).exists()` is `False`:
        - Log error.
        - If `self.throw_error_on_load` is `True` $\rightarrow$ Raise `FileNotFoundError`.
        - If `self.throw_error_on_load` is `False` $\rightarrow$ Set `self.loaded = False` and terminate.
    - **File Existence Success**: If `True` $\rightarrow$ Read text and set `self.loaded = True`.

## 4. Resource Dependencies
- **Standard Libraries**: `logging`, `os.path` (exists), `pathlib` (Path)
- **Internal Modules**: None
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: `THROW_ERROR_ON_LOAD_CONTEXT_FILE_NOT_EXIST = False`
- **Environment Lookups**: None