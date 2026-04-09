## 1. Architectural Role
The `MessageOrchestrator` class is responsible for managing the execution flow and coordination of agents within a pipeline, handling user input, and orchestrating the interaction between agents and tools.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `MessageOrchestrator` | Class | Orchestrates the execution of agents in a pipeline, handling user input and coordinating interactions between agents and tools. |
| `run_loop` | Method | Main execution loop that processes user prompts and orchestrates agent interactions. |
| `_prepare_payload` | Method | Prepares the payload for sending to an agent, including user input, agent memory, and context. |
| `_process_agent_response` | Method | Processes the response from an agent, handles tool execution, and manages agent transitions. |
| `_handle_tool_execution` | Method | Executes a specific tool, handles authorization, and updates the context with the tool's result. |
| `_call_specialist_worker` | Method | Calls a specialist worker to handle high-complexity tasks. |
| `_gatekeeper` | Method | Authorizes tool execution based on user input and configuration. |
| `_handle_agent_outputs` | Method | Handles outputs from agents, including messages to the user and updates to agent memory. |
| `_update_stagnation_tracking` | Method | Tracks the repetition of actions to detect potential stagnation. |
| `_validate_target` | Method | Validates the target agent for inter-agent communication. |
| `_handle_inter_agent_messaging` | Method | Handles messaging between agents. |

## 3. Execution Logic & Flow
- **Initialization**: The `MessageOrchestrator` class is initialized with a `connector`, `registry`, and `pipeline_config`. It sets up the initial state, including the agents, history, and context.
- **Data Path**: User input is processed through the `run_loop`, which calls `_prepare_payload` to create a payload for the current agent. The agent's response is then processed by `_process_agent_response`, which handles tool execution and agent transitions.
- **Conditional Branching**: Key decision points include:
  - Determining the next agent to interact with based on the current agent's response.
  - Handling tool execution, including authorization and calling the specialist worker for high-complexity tasks.
  - Validating the target agent for inter-agent communication.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `copy`, `json`, `re`
- **Internal Modules**: `functions`, `color`, `terminal_ui`, `agents.agent_tools`
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: `MAX_ITERATIONS`, `MANAGER_AGENT_ROLE`
- **Environment Lookups**: None