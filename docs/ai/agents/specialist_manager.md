

## 1. Architectural Role  
Manages invocation of specialist LLM workers for high-complexity, unstructured generation tasks like file writing/patching by resolving file paths, capturing current state, and routing requests to configured specialists.  

## 2. Interface & API Surface  
| Entity | Type | Functional Responsibility |  
| :--- | :--- | :--- |  
| `SpecialistManager` | Class | Coordinates specialist LLM workers for task execution |  
| `is_specialist_tool` | Method | Validates if a tool name corresponds to a registered specialist |  
| `invoke` | Method | Executes a specialist worker by injecting task context, goal, and file state |  

## 3. Execution Logic & Flow  
- **Initialization**: Stores `connector` and `specialist_config` as instance variables.  
- **Data Path**:  
  1. Extracts `tool_name` and `params` from invocation.  
  2. Retrieves `role_description` from `specialist_config`.  
  3. Derives `goal` from `params` (priority: `instructions`  `content`  `replace`).  
  4. Resolves `path` via `_resolve_path`, reads file content (if exists) for `current_state`.  
  5. Constructs `worker_payload` with task context and sends via `connector.send_raw_request`.  
- **Conditional Branching**:  
  - Checks if `path` exists and reads content (capped at 3000 chars).  
  - Catches exceptions during path resolution to avoid crash propagation.  

## 4. Resource Dependencies  
- **Standard Libraries**: `os`, `typing`  
- **Internal Modules**: `agents.agent_tools` (for `_resolve_path`)  
- **External Packages**: None  

## 5. Configuration & Environment  
- **Hardcoded Constants**:  
  - `"Complete task."` (default goal if no explicit instructions)  
  - `"File does not exist yet or is empty."` (default current_state)  
- **Environment Lookups**:  
  - `os.getenv` (indirectly via `_resolve_path` for path resolution)