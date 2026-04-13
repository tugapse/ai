

## 1. Architectural Role  
Orchestrate multi-agent pipeline execution, routing messages between agents, managing state, and executing tools via a defined configuration.  

## 2. Interface & API Surface  
| Entity | Type | Functional Responsibility |  
| :--- | :--- | :--- |  
| `MessageOrchestrator` | Class | Central coordinator for agent message routing, state management, and tool execution. |  
| `run_loop` | Method | Main orchestration loop for agent task execution and pipeline progression. |  
| `_prepare_payload` | Method | Construct input payload for agents, integrating history, context, and objectives. |  
| `_process_agent_response` | Method | Parse agent responses, handle tool execution, and determine next agent transitions. |  
| `_handle_tool_execution` | Method | Execute tools with authorization checks and specialist interception for complex tasks. |  
| `_gatekeeper` | Method | Prompt user for authorization on sensitive tools like `execute_command`. |  
| `SpecialistManager` | Dependency | Manages specialist workers for high-complexity tools like file patching. |  
| `MemoryManager` | Dependency | Tracks agent-specific messages, history, and notes. |  
| `VectorMemory` | Dependency | Optional long-term memory store for contextual recall. |  
| `TerminalUI` | Dependency | Provides UI feedback for status, errors, and user prompts. |  

## 3. Execution Logic & Flow  
- **Initialization**: Loads connector, registry, pipeline config, and initializes memory/vector memory systems.  
- **Data Path**: User prompt  injected into entry-point agent  payload prepared with context/history  agent response parsed  response routed to next agent or user.  
- **Conditional Branching**:  
  - Format error detection (3 strikes  pipeline halts).  
  - Tool authorization checks (manual prompts for `execute_command`).  
  - Target validation (ensures transitions to allowed agents or stops).  

## 4. Resource Dependencies  
- **Standard Libraries**: `os`, `copy`, `json`  
- **Internal Modules**: `specialist_manager`, `memory_manager`, `vector_memory`, `terminal_ui`, `functions`, `color`  
- **External Packages**: None explicitly referenced.  

## 5. Configuration & Environment  
- **Hardcoded Constants**: `MAX_ITERATIONS=100`, `MANAGER_AGENT_ROLE="management"`  
- **Environment Lookups**: None explicitly used in provided code.