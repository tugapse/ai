## 1. Architectural Role

**Functional Mission**
The **tool_loader.py** component serves as a dynamic discovery and injection engine for extending the system's capabilities at runtime. Its primary mission is to scan designated filesystem directories for Python modules, perform safe imports, and identify specific functions decorated with the `_is_tool` attribute to facilitate automated tool registration.

**System Context & Integration**
This component acts as a bridge between the local filesystem and the [ToolRegistry](/docs/tools/tool_registry.md). By modifying `sys.path` and `sys.modules` temporarily, it enables user-defined scripts to function as first-class citizens within the architecture, allowing for complex cross-module imports within the toolset itself. Once identified, these tools are handed off to the [ToolRegistry](/docs/tools/tool_registry.md) to be made available to downstream agents and execution engines.

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- No hardcoded constants identified.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `load_and_register_user_tools` | Func | Orchestrates the directory scanning, module importing, and registration process for tools marked with `_is_tool`. |

## 4. Execution Logic & Flow
- **Initialization**: Validates the existence of the `user_tools_dir`. If invalid, logs a warning via [functions](/docs/functions.md) and aborts.
- **Data Path**: 
    1. **Path Setup**: Injects `user_tools_dir` into `sys.path` to support relative imports between tools.
    2. **Discovery**: Iterates through files in `user_tools_dir`, filtering for `.py` files that do not start with an underscore.
    3. **Importation**: Uses `importlib.util` to create a module spec, loads the module into `sys.modules`, and executes it.
    4. **Inspection**: Iterates through all attributes of the loaded module using `dir()`.
    5. **Registration**: Checks if an attribute is callable and possesses the `_is_tool` flag; if true, calls `registry.register_tool()`.
    6. **Cleanup**: Removes `user_tools_dir` from `sys.path` upon completion.
- **Conditional Branching**:
    - **Directory Check**: If `os.path.isdir` is false, the process exits early.
    - **Import Error**: If `spec.loader.exec_module` fails, an `ImportError` is raised after logging the error via [functions](/docs/functions.md).
    - **Tool Identification**: Only attributes where `hasattr(func_ref, "_is_tool")` is true are processed for registration.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `sys`, `importlib.util`, `inspect`, `typing`
- **Internal Modules**: 
    - [functions](/docs/functions.md)
    - [ToolRegistry](/docs/tools/tool_registry.md)
- **External Packages**: None identified.