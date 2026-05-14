## 1. Architectural Role
Acts as a dynamic plugin loader that scans a filesystem directory to import Python modules and register functions decorated with `_is_tool` into a centralized registry.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `load_and_register_user_tools` | Func | Orchestrates directory scanning, module injection into `sys.path`/`sys.modules`, and tool registration via the provided registry. |

## 3. Execution Logic & Flow
- **Initialization**: Imports `os`, `sys`, `importlib.util`, `inspect`, and `functions` to prepare the environment for filesystem traversal and module manipulation.
- **Data Path**: `user_tools_dir` (String) $\rightarrow$ Directory Scan (Filesystem) $\rightarrow$ Module Spec Creation (`importlib`) $\rightarrow$ Module Execution (`exec_module`) $\rightarrow$ Attribute Inspection (`dir`) $\rightarrow$ `registry.register_tool` (Side Effect).
- **Conditional Branching**:
    - **Directory Validation**: If `user_tools_dir` is not a valid directory, logs a warning and exits.
    - **File Filtering**: Processes only files ending in `.py` that do not start with `_`.
    - **Module Loading**: Checks if `spec` and `spec.loader` are valid before attempting execution.
    - **Tool Identification**: Checks if an attribute is `callable` AND possesses `_is_tool` attribute AND `_is_tool` is truthy.
    - **Error Handling**: If an exception occurs during module execution, logs an error and raises `ImportError`.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `sys`, `importlib.util`, `inspect`, `typing`
- **Internal Modules**: `functions` (aliased as `func`)
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: None.
- **Environment Lookups**: None.