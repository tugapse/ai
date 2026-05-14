## 1. Architectural Role
Acts as a specialized orchestration layer that delegates high-complexity generation tasks to specific LLM workers by mapping tool names to unique role descriptions and providing them with file-state context.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `SpecialistManager` | Class | Manages the lifecycle and invocation of specialist LLM workers. |
| `__init__` | Method | Initializes the manager with an LLM connector and a tool-to-role mapping configuration. |
| `is_specialist_tool` | Method | Validates if a given tool name exists within the provided specialist configuration. |
| `invoke` | Method | Executes a specialist request by constructing a task context (target path, file content, and goal) and streaming the raw text response. |

## 3. Execution Logic & Flow
- **Initialization**:
    1. Receives `connector` (LLM interface) and `specialist_config` (mapping dict).
    2. Stores these as `self.connector` and `self.config`.
- **Data Path**:
    1. **Input**: `tool_name` (str) and `params` (Dict containing `instructions`/`content`/`replace` and `path`).
    2. **Context Assembly**: 
        - Retrieves `role_description` from `self.config`.
        - Extracts `goal` from `params` via prioritized key lookup.
        - Resolves `path` via `_resolve_path`.
        - Reads up to 3000 characters of the existing file at `resolved_path` to establish `current_state`.
    3. **Payload Construction**: Builds `worker_payload` containing `task_context` (Path + State + Goal) and a strict `instruction` for raw text output.
    4. **Processing**: Passes payload and `role_description` to `self.connector.send_raw_request`.
    5. **Output**: Aggregates the `raw_output_stream` into a single string and applies `.strip()`.
- **Conditional Branching**:
    - `is_specialist_tool`: Returns `True` if `tool_name` is a key in `self.config`, otherwise `False`.
    - `invoke` (File Access): If `os.path.exists(resolved_path)` is true, reads file; otherwise, defaults `current_state` to "File does not exist yet or is empty."
    - `invoke` (Goal Extraction): Cascades through `instructions` $\rightarrow$ `content` $\rightarrow$ `replace` $\rightarrow$ "Complete task."

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `typing`
- **Internal Modules**: `tools.agent_tools._resolve_path`

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `3000`: Maximum character limit for file state context.
    - `"unknown"`: Default value for missing path.
    - `"Complete task."`: Default fallback for missing instructions.
    - `"File does not exist yet or is empty."`: Default fallback for missing file content.
    - `"Output raw text only. Do not use markdown blocks or explanations."`: Hardcoded instruction to the LLM.
- **Environment Lookups**: None.