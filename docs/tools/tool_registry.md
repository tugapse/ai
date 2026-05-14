## 1. Architectural Role
Provides a singleton registry for managing the registration, metadata retrieval, and execution of callable tool functions within the system.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ToolRegistry` | Class | Manages a centralized singleton collection of tool functions and their execution lifecycle. |
| `register_tool` | Method | Maps a unique string name to a callable object and logs the registration. |
| `get_tool_info` | Method | Retrieves and formats the docstring of a registered tool for descriptive output. |
| `execute_tool` | Method | Validates tool existence, processes input parameters, and invokes the registered callable within a try-except block. |
| `get_all_tools` | Method | Returns the internal dictionary containing all registered tool mappings. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. The `__new__` method implements a Singleton pattern, checking if `_instance` is `None`.
    2. If `None`, a new instance is created and `_tools` is initialized as an empty `Dict[str, Callable]`.
    3. The `__init__` method is called but performs no additional state modification.
- **Data Path**:
    1. **Registration**: `name` (str) + `func_ref` (Callable) $\rightarrow$ `_tools` dictionary update $\rightarrow$ `func.debug` log.
    2. **Metadata Retrieval**: `name` (str) $\rightarrow$ `_tools[name]` lookup $\rightarrow$ `__doc__` extraction $\rightarrow$ string formatting $\rightarrow$ indented docstring.
    3. **Execution**: `name` (str) + `params` (Dict) $\rightarrow$ Existence check $\rightarrow$ `params` type validation $\rightarrow$ `func.log` $\rightarrow$ `_tools[name](**p)` $\rightarrow$ Result `Dict`.
- **Conditional Branching**:
    1. **Singleton Check**: If `_instance` exists, skip creation and return existing instance.
    2. **Tool Existence**: In `get_tool_info` and `execute_tool`, check if `name` exists in `_tools`; if not, return error/placeholder string.
    3. **Parameter Validation**: In `execute_tool`, check if `params` is an instance of `dict`; if not, default to `{}`.
    4. **Error Handling**: In `execute_tool`, catch all `Exception` types to prevent registry crash, returning a `FAILED` status dictionary.

## 4. Resource Dependencies
- **Standard Libraries**: `typing` (`Dict`, `Any`, `Callable`)
- **Internal Modules**: `functions` (aliased as `func`)

## 5. Configuration & Environment
- **Hardcoded Constants**: None.
- **Environment Lookups**: None.