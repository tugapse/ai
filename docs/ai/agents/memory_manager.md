

## 1. Architectural Role  
Manages the state and communication between agents and the orchestrator pipeline, maintaining historical data, task tracking, and tool execution results.  

## 2. Interface & API Surface  
| Entity | Type | Functional Responsibility |  
| :--- | :--- | :--- |  
| `AgentMemory` | Class | Stores agent-specific state, including notes, received messages, history, tasks, and manifest. |  
| `OrchestratorContext` | Class | Holds global pipeline state, including tool results, task plans, step indices, and action history. |  
| `MemoryManager` | Class | Orchestrates agent memory management, message routing, tool result logging, and stagnation detection. |  
| `__init__` | Method | Initializes the MemoryManager with agent names, creating agent memory instances and an orchestrator context. |  
| `get_agent_memory` | Method | Retrieves an agent's memory object for read/write operations. |  
| `add_message_to_agent` | Method | Appends a message payload to a target agent's received messages queue. |  
| `record_tool_result` | Method | Logs tool execution results to the orchestrator context and notifies the agent. |  
| `update_agent_history_and_notes` | Method | Syncs agent memory with new notes, history, and response data from external inputs. |  
| `check_stagnation` | Method | Detects repetitive tool calls by analyzing action history fingerprints. |  

## 3. Execution Logic & Flow  
- **Initialization**: Loads agent names, instantiates `OrchestratorContext` and `AgentMemory` objects for each agent.  
- **Data Path**: Input messages are queued for agents; tool results are logged to context and relayed to agents. Agent history is updated by moving received messages to history and appending new interactions.  
- **Conditional Branching**: `check_stagnation` evaluates if the same tool call fingerprint appears 3 times in the last 5 entries, triggering a stagnation flag.  

## 4. Resource Dependencies  
- **Standard Libraries**: `json` (for serializing tool parameters).  
- **Internal Modules**: None directly referenced in this file.  
- **External Packages**: None used in this file.  

## 5. Configuration & Environment  
- **Hardcoded Constants**: None.  
- **Environment Lookups**: None.