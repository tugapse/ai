## 1. Architectural Role
This module serves as the dynamic plugin ingestion engine for the system, responsible for scanning external directories to discover and instantiate functional extensions. It utilizes Python's `importlib` machinery to perform runtime module loading, enabling the system to extend its capabilities without core code modification by identifying functions decorated with specific metadata and registering them into the [tools/tool_registry.md](tools/tool_registry.md) instance.

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- No hardcoded constants identified.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `load_and_register_user_tools` | Func | Orchestrates directory scanning, module importing, and registration of tool-marked functions into the provided registry. |

## 4. Execution Logic & Flow
- **Initialization**: Receives a `registry` object (conforming to [tools/tool_registry.md](tools/tool_registry.md)) and a `user_tools_dir` string path.
- **Data Path**: 
    1. **Validation**: Checks if `user_tools_dir` exists via `os.path.isdir`.
    2. **Path Injection**: Prepends `user_tools_dir` to `sys.path` to facilitate intra-tool relative imports.
    3. **Discovery**: Iterates through files in `user_tools_dir`, filtering for non-private `.py` files.
    4. **Loading**: Creates a module spec via `importlib.util`, executes the module, and injects it into `sys.modules`.
    5. **Inspection**: Traverses module attributes to find callables possessing the `_is_tool` attribute.
    6. **Registration**: Passes discovered functions to `registry.register_tool`.
    7. **Cleanup**: Removes `user_tools_dir` from `sys.path` upon completion.
- **Conditional Branching**:
    - If directory is missing: Logs warning and aborts.
    - If module loading fails: Logs error and raises `ImportError`.
    - If `_is_tool` is True: Proceeds to registration.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `sys`, `importlib.util`, `inspect`, `typing`
- **Internal Modules**: 
    - [functions](functions.md)
    - [tools/tool_registry.md](tools/tool_registry.md)
- **External Packages**: None