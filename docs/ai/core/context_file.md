

## 1. Architectural Role  
Manages file loading into context with existence validation and error control.  

## 2. Interface & API Surface  
| Entity | Type | Functional Responsibility |  
| :--- | :--- | :--- |  
| `ContextFile` | Class | Encapsulates file loading logic and content management |  
| `__init__` | Method | Initializes file path, error handling flag, and state variables |  
| `load` | Method | Loads file content, validates existence, and manages error raising |  

## 3. Execution Logic & Flow  
- **Initialization**: Sets `filename`, `content`, `loaded`, `throw_error_on_load`, and initializes a logger instance.  
- **Data Path**: Input `filename`  Check existence via `Path.exists()`  Read content via `Path.read_text()`  Assign to `content` and set `loaded=True`.  
- **Conditional Branching**: If file not found  Log error  Raise `FileNotFoundError` if `throw_error_on_load` is True.  

## 4. Resource Dependencies  
- **Standard Libraries**: `logging`, `os.path`, `pathlib`  
- **Internal Modules**: None  
- **External Packages**: None  

## 5. Configuration & Environment  
- **Hardcoded Constants**: `THROW_ERROR_ON_LOAD_CONTEXT_FILE_NOT_EXIST` (default: `False`)  
- **Environment Lookups**: None