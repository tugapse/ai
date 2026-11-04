## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **Program** | [src/ai/program.py](/src/ai/program.py) |

The `Program` class serves as the central orchestrator for the JARVIS system. Its primary responsibility is to coordinate the lifecycle of various services, including Large Language Model (LLM) management, hardware/software module orchestration, user interface feedback, and session persistence. It acts as the glue between high-level user interactions and the low-level execution of tools and agentic loops.

In the broader system architecture, this component functions as the main controller. It manages the transition from configuration loading to the active chat loop, handles the "Thought-Action" cycle of the autonomous agent, and ensures that all componentsfrom [VectorMemory](/ai/modules/vector_memory/vector_memory.md) to the [UIOrchestrator](/ai/services/ui_orchestrator.md)are properly initialized, synchronized, and shut down.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `load_config(args=None)` | Method | Loads the `ProgramConfig` and initializes core services like `ModelOrchestrator`, `HistoryManager`, and `UIOrchestrator`. |
| `init_config(args)` | Method | Applies CLI arguments to the configuration and triggers module loading via the `ModuleRegistry`. |
| `init_program()` | Method | Sets up session paths, initializes the UI, and loads the tool registry. |
| `start_chat(user_input: Optional[str])` | Method | Entry point for a user interaction turn; initiates the autonomous agent loop. |
| `run()` | Method | Starts the main operational loop, binds core events, and enters the primary chat interface. |
| `shutdown()` | Method | Performs an aggressive, controlled shutdown of all services and releases memory. |
| `route_session(filepath: str)` | Method | Switches the active chat session to a different history file. |
| `llm` | Property | Lazy-loader for the active `BaseModel` instance. |
| `model_params` | Property | Returns the current configuration parameters for the active LLM. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The component implements an autonomous agent loop within `_run_agent_loop`. This loop follows a continuous cycle: performing LLM inference $\rightarrow$ processing stream results via `StreamOrchestrator` $\rightarrow$ executing tool calls via `ToolRegistry` $\rightarrow$ appending results back to chat history $\rightarrow$ repeating until a completion signal is received. It also includes a "Sentinel" mechanism that injects system warnings if the loop exceeds a maximum step count to prevent infinite recursion.
- **Side Effects:** 
    - **Filesystem:** Writes chat history to disk via `HistoryManager` and reads system prompts and tool definitions from the filesystem.
    - **Hardware/IO:** Interacts with terminal output for UI, manages audio collection if a voice module is active, and manages process-level shutdown.
    - **State Mutation:** Heavily mutates the `Chat` object and the `ToolRegistry` during runtime.
- **Error Handling:** Uses a broad `try...except` block in `start_chat` to catch critical errors, logging them via `func.log` and triggering an LLM shutdown to prevent unstable states. It also implements a Human-In-The-Loop (HIL) gatekeeper for sensitive tools, requiring explicit user confirmation via standard input.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- `ProgramConfig`  Managed via `ai.config`, defines model settings, session paths, and module enablement.
- `args`  CLI arguments used to override configurations and enable specific modules.

**Module Dependencies:**
- **Standard/External:** `os`, `traceback`, `gc`, `json`, `typing`.
- **Internal:**
    - [Chat](/ai/chat/chat.md)
    - [BaseModel](/ai/core/llms/base_llm.md)
    - [ProgramConfig](/ai/config.md)
    - [Agent](/ai/agents/agent.md)
    - [VectorMemory](/ai/modules/vector_memory/vector_memory.md)
    - [BaseVoiceModule](/ai/modules/voice/base_module.md)
    - [ToolRegistry](/ai/tools/tool_registry.md)
    - [AVAILABLE_TOOLS](/ai/tools/agent_tools.md)
    - [load_and_register_user_tools](/ai/tools/tool_loader.md)
    - [SessionManager](/ai/services/session_manager.md)
    - [PromptLoader](/ai/services/prompt_loader.md)
    - [CliConfig](/ai/services/config_helper.md)
    - [EventBinder](/ai/services/event_binder.md)
    - [ModelOrchestrator](/ai/services/model_orchestrator.md)
    - [HistoryManager](/ai/services/history_manager.md)
    - [ModuleRegistry](/ai/services/module_registry.md)
    - [UIOrchestrator](/ai/services/ui_orchestrator.md)
    - [StreamOrchestrator](/ai/services/stream_orchestrator.md)
    - [ai.functions](/ai/functions.md)
    - [Color](/ai/color.md)