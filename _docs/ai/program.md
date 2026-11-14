## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| Program | /ai/program.md |

This component serves as the primary orchestrator for the entire JARVIS application. Its core responsibility is managing the lifecycle of the AI system, which includes initializing configuration, loading necessary modules, setting up the LLM backend, and managing the high-level interaction flow between the user, the LLM, and external tools. It coordinates complex interactions like autonomous agent execution and conversational turns.

Architecturally, `Program` acts as the main controller, sitting at the apex of the application stack. It relies heavily on services like [SessionManager](/ai/services/session_manager.md), [ModelOrchestrator](/ai/services/model_orchestrator.md), and [ToolRegistry](/ai/tools/tool_registry.md) to handle persistence, inference, and functionality, respectively. It drives the main execution loop via [EventBinder](/ai/services/event_binder.md).

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| `Program.__init__` | Method | Initializes core state variables, including the Chat instance and ToolRegistry. |
| `Program.llm` | Property | Lazy-loads and returns the initialized [BaseModel](/ai/core/llms/base_llm.md) instance. |
| `Program.model_params` | Property | Retrieves the current configuration parameters used for LLM inference. |
| `Program.load_config` | Method | Loads the primary `ProgramConfig` from provided arguments and initializes several key services. |
| `Program.init_config` | Method | Applies CLI arguments to the configuration and loads enabled modules via [ModuleRegistry](/ai/services/module_registry.md). |
| `Program.init_program` | Method | Performs high-level setup, initializing session paths, the UI, and loading the tool registry. |
| `Program.start_chat` | Method | Executes the interaction turn by running the Agent Loop, handling user input and streaming orchestration. |
| `Program.run` | Method | Starts the main operational loop, binds system events, and manages the primary application lifecycle. |
| `Program.shutdown` | Method | Performs a controlled shutdown, ensuring the LLM connection is terminated and resources are released. |
| `Program.route_session` | Method | Switches the active chat session to a specified file path by interacting with [HistoryManager](/ai/services/history_manager.md). |

## 3. Implementation Details & Side Effects
- **Core Logic:** The program operates around two primary loops: the main event loop initiated by `run()`, and the internal "Thought-Action" loop within `_run_agent_loop()`. This latter loop iteratively calls the LLM, checks for tool calls, executes those tools via [ToolRegistry](/ai/tools/tool_registry.md), and updates the chat history until a natural completion or an interruption occurs. State management is crucial, utilizing `ProcessManager` to track activity.
- **Side Effects:** Reads/writes to filesystem (via `SessionManager` and `HistoryManager`), interacts with the network (via `BaseModel` for LLM API calls), and directly manipulates console output via `func.out` and `func.log`.
- **Error Handling:** Catches `LLMAPIError` during chat turns to gracefully report remote failures. General exceptions are caught in `start_chat` to log critical errors and trigger LLM shutdown. The agent loop includes a sentinel warning mechanism (`_inject_sentinel_warning`) to prevent infinite loops.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `os`, `traceback`, `gc`, `json`, `typing`.
- **Internal:** [Chat](/ai/chat/chat.md), [BaseModel](/ai/core/llms/base_llm.md), [ProgramConfig](/ai/config.md), [ProgramSetting](/ai/config.md), [Color](/ai/color.md), [LLMAPIError](/ai/core/llms/api_retry.md), [Agent](/ai/agents/agent.md), [VectorMemoryModule](/ai/modules/vector_memory/vector_memory_module.md), [VectorMemory](/ai/modules/vector_memory/vector_memory.md), [BaseVoiceModule](/ai/modules/voice/base_module.md), [ToolRegistry](/ai/tools/tool_registry.md), [ToolLoader](/ai/tools/tool_loader.md), [SessionManager](/ai/services/session_manager.md), [PromptLoader](/ai/services/prompt_loader.md), [CliConfig](/ai/services/config_helper.md), [EventBinder](/ai/services/event_binder.md), [ModelOrchestrator](/ai/services/model_orchestrator.md), [HistoryManager](/ai/services/history_manager.md), [ModuleRegistry](/ai/services/module_registry.md), [UIOrchestrator](/ai/services/ui_orchestrator.md), [StreamOrchestrator](/ai/services/stream_orchestrator.md), [ProcessManager](/ai/services/process_manager.md), [ai.functions](/ai/functions.md).