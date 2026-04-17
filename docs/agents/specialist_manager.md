## 1. Architectural Role
Coordinates the delegation of high-complexity generation tasks to specialized LLM workers by resolving file contexts and managing raw text output streams.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `SpecialistManager` | Class | Orchestrates the lifecycle and invocation of specialist LLM workers. |
| `SpecialistManager.__init__` | Method | Initializes the manager with a connector and a mapping of tool names to role descriptions. |
| `SpecialistManager.is_specialist_tool` | Method | Validates if a given `tool_name` is registered in the specialist configuration. |
| `SpecialistManager.invoke` | Method | Processes tool parameters, retrieves file state, and executes a raw request via the connector. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. Receives `connector` (LLM interface) and `specialist_config` (Role mapping).
    2. Stores these as `self.connector` and `self.config`.
- **Data Path**: 
    1. **Input**: `tool_name` and `params` (containing instructions/content/replace and path).
    2. **Context Retrieval**: 
        - Resolves `path` via `_resolve_path`.
        - Checks if file exists; if so, reads the first 3000 characters.
    3. **Payload Construction**: Combines `path`, `current_state`, and `goal` into `task_context`.
    4. **Execution**: Sends `worker_payload` and `role_description` to `self.connector.send_raw_request`.
    5. **Output**: Aggregates the raw output stream into a single stripped string.
- **Conditional Branching**:
    - **Goal Selection**: Prioritizes `instructions` $\rightarrow$ `content` $\rightarrow$ `replace` $\rightarrow$ default "Complete task."
    - **File Access**: If `_resolve_path` fails or file is missing, `current_state` defaults to "File does not exist yet or is empty."

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `typing`
- **Internal Modules**: `agents.agent_tools` (`_resolve_path`)
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `3000`: Maximum character limit for reading the current state of a file.
    - `"Output raw text only. Do not use markdown blocks or explanations."`: Static instruction sent to all specialist workers.
- **Environment Lookups**: None