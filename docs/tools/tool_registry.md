## 1. Architectural Role

**Functional Mission**
The **ToolRegistry** class serves as a centralized, singleton repository for managing the lifecycle and discovery of executable tool functions within the system. Its primary mission is to provide a unified interface for registering arbitrary callables and retrieving them via string identifiers, effectively decoupling the definition of tools from their invocation logic.

**System Context & Integration**
This component acts as a critical bridge between the agentic reasoning layer and the system's functional capabilities. It is designed to be consumed by orchestration modules that require dynamic tool invocation based on model outputs. By maintaining a single source of truth for available tools, it facilitates the transition from high-level intent (provided by LLMs) to low-level execution, ensuring that tool metadata and execution logic are consistently accessible across the architecture.

## 2. Environment & Configuration
**Environment Lookups:**
No environment lookups identified.

**Hardcoded Constants:**
No hardcoded constants identified.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ToolRegistry` | Class | Implements a Singleton pattern to manage a global registry of tool functions. |
| `register_tool` | Method | Maps a unique string name to a callable function reference in the internal registry. |
| `get_tool_info` | Method | Retrieves and formats the docstring of a registered tool for model consumption. |
| `execute_tool` | Method | Dynamically invokes a registered tool with provided parameters, including error handling. |
| `get_all_tools` | Method | Returns the complete dictionary of registered tool mappings. |

## 4. Execution Logic & Flow
- **Initialization**: The `__new__` method implements a Singleton pattern, ensuring only one instance of `_tools` exists. The `_tools` dictionary is initialized upon the first instantiation to store `Callable` references.
- **Data Path**: 
    - **Registration**: `name` (str) + `func_ref` (Callable) $\rightarrow$ `_tools` dictionary.
    - **Information Retrieval**: `name` (str) $\rightarrow$ Lookup `_tools[name]` $\rightarrow$ Extract `__doc__` $\rightarrow$ String formatting $\rightarrow$ Indented docstring.
    - **Execution**: `name` (str) + `params` (Dict) $\rightarrow$ Lookup `_tools[name]` $\rightarrow$ Parameter validation $\rightarrow$ Function invocation (`**p`) $\rightarrow$ Result Dict.
- **Conditional Branching**:
    - **Tool Existence Check**: In `get_tool_info` and `execute_tool`, if the requested `name` is not in `_tools`, the system returns a fallback string or a `FAILED` status dictionary.
    - **Parameter Validation**: In `execute_tool`, an `isinstance` check (noted as `isinstance` in source) determines if `params` is a valid dictionary; if not, it defaults to an empty dictionary.
    - **Exception Handling**: The `execute_tool` method wraps the function call in a `try-except` block to catch runtime errors during tool execution, returning a `FAILED` status instead of crashing the registry.

## 5. Resource Dependencies
- **Standard Libraries**: `typing` (Dict, Any, Callable)
- **Internal Modules**: 
    - [functions](/docs/functions.md)
- **External Packages**: None identified.