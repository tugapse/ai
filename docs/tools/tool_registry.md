## 1. Architectural Role
Acts as a centralized Singleton registry for managing the lifecycle of executable tool functions within the system. It provides a unified interface for registering callables, retrieving metadata/documentation for tool discovery, and executing tools via dynamic parameter unpacking, serving as the primary dispatch mechanism for agentic capabilities defined in [tools/tool_loader.md](tools/tool_loader.md) and [tools/agent_tools.md](tools/agent_tools.md).

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- No hardcoded constants identified.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ToolRegistry` | Class | Singleton container managing the mapping of tool names to callable functions. |
| `register_tool` | Method | Maps a string identifier to a function reference in the internal registry. |
| `get_tool_info` | Method | Extracts and formats docstrings from registered functions for LLM context/description. |
| `execute_tool` | Method | Invokes a registered function with provided keyword arguments and handles execution errors. |
| `get_all_tools` | Method | Returns the raw dictionary of all registered tool mappings. |

## 4. Execution Logic & Flow
- **Initialization**: 
    - Employs the Singleton pattern via `__new__` to ensure `_instance` is unique.
    - Initializes `_tools` as an empty `Dict[str, Callable]` on the first instantiation.
- **Data Path**:
    - **Registration**: `name` (str) + `func_ref` (Callable) $\rightarrow$ `_tools` dictionary.
    - **Discovery**: `name` (str) $\rightarrow$ `_tools[name].__doc__` $\rightarrow$ Formatted string with indentation.
    - **Execution**: `name` (str) + `params` (Dict) $\rightarrow$ Parameter validation $\rightarrow$ `**kwargs` unpacking $\rightarrow$ Function Return $\rightarrow$ `Dict[str, Any]`.
- **Conditional Branching**:
    - `get_tool_info`: Checks existence of `name` in `_tools`; if missing, returns fallback string.
    - `execute_tool`: Checks existence of `name` in `_tools`; if missing, returns failure status.
    - `execute_tool`: Validates if `params` is a dictionary; if not, defaults to an empty dictionary `{}`.
    - `execute_tool`: Wraps execution in a `try/except` block to catch and return runtime errors without crashing the caller.

## 5. Resource Dependencies
- **Standard Libraries**: `typing`
- **Internal Modules**: 
    - [functions](functions.md)
- **External Packages**: None identified.