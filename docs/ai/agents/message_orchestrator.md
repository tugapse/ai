## Module Purpose
This module defines the `MessageOrchestrator` class, which is responsible for managing the execution flow of an AI agent pipeline, coordinating messages between agents, handling tool execution, and tracking pipeline state and agent memory.

## Interface & Exports
- `MessageOrchestrator`: The primary class that orchestrates the AI agent pipeline.
    - `__init__(self, connector: Any, registry: Any, pipeline_config: Dict[str, Any])`: Initializes the orchestrator with a connector, tool registry, and pipeline configuration.
    - `run_loop(self, user_prompt: str)`: Executes the main loop of the agent pipeline, processing agent responses and managing transitions.

## Internal Logic
The `MessageOrchestrator` class manages an iterative loop where a `current_agent` processes a task. It prepares a payload for the agent, sends a request via a `connector`, and processes the agent's JSON response. Key internal logic includes:
- **Agent State Management**: Each agent has its own memory (`agent_memory`) storing notes, received messages, history, and current task.
- **Tool Execution**: When an agent requests a tool, the orchestrator checks for authorization (`_gatekeeper`), potentially invokes a "Specialist" worker (`_call_specialist_worker`) for high-complexity tools (`write_file`, `patch_file`, `generate_doc`), and executes the tool via the `registry`.
- **Response Processing**: Agent responses are parsed for actions (tool calls, agent transitions, user interaction), manifest updates, and messages.
- **Inter-Agent Messaging**: Messages and tasks can be directed to other agents or the `USER`.
- **Stagnation Tracking**: The `_update_stagnation_tracking` method monitors repeated tool calls to detect potential infinite loops.
- **Error Handling**: Tracks consecutive JSON format failures and halts the pipeline if an agent gets stuck in a format loop.
- **Context Management**: Maintains a `context` dictionary for tool results, plan, current step, and file information.
- **Payload Preparation**: Constructs a detailed payload for agents, including objective, notes, messages, conversation history, plan, and recent tool outcomes.

## Dependencies
- `os`
- `copy`
- `json`
- `re`
- `typing.Dict`
- `typing.Any`
- `typing.Optional`
- `functions` (aliased as `func`)
- `color` (aliased as `Color`)
- `terminal_ui.TerminalUI`
- `agents.agent_tools._resolve_path`

## Constants & Environment
- `MAX_ITERATIONS`: `100` (Maximum number of iterations for the `run_loop`).
- `MANAGER_AGENT_ROLE`: `"management"` (Role identifier for manager agents).