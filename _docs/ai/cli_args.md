## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| CliArgs | /ai/cli_args.md |

This component serves as the primary entry point and command-line interface (CLI) dispatcher for the JARVIS application. Its core responsibility is to parse user-provided command-line arguments and, based on the combination of flags, determine the correct operational mode for the application. This mode can be Standalone (one-shot execution), Server (running the BrainHub API), or Client (running an agent interaction loop).

Architecturally, `CliArgs` acts as the central controller for initialization and mode routing. It coordinates various services—such as `DirectoryManager` for file handling, `ProgramConfig` for system settings, and specific handlers like `_handle_server_mode` or `_handle_agent_mode`—to bootstrap the correct execution context. It bridges the raw command-line input into structured operational commands for the rest of the system, interacting with services like [AgentSessionManager](/ai/agents/session_manager.md) and [BrainHub](/ai/modules/server/brain_hub.md).

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| CliArgs | Class | Main orchestrator for CLI input. Handles mode dispatching and ensures proper initialization based on the user's intent. |
| parse_args | Method | The main dispatcher. Analyzes arguments to decide if JARVIS acts as a Brain (Server), a Body (Client), or a Standalone agent. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The `parse_args` method executes a series of checks (e.g., `--frontend`, `--install`, `--list-sessions`) before dispatching to mode handlers. Mode dispatching prioritizes Server mode, falls back to local direct mode, and finally checks for agent execution flags. Agent execution involves consolidating input from multiple sources (task files, command-line arguments, piped stdin) before invoking the `run_one_shot` function.
- **Side Effects:** Reads/writes to the filesystem (e.g., reading configuration, creating tool skeletons, loading task templates, reading chat logs). Spawns processes (during installation mode). Interacts with the network when starting the server mode. Mutates global state via `Program` instance.
- **Error Handling:** Explicitly handles `KeyboardInterrupt` for graceful server shutdown. Uses `sys.exit()` extensively to terminate the program upon successful completion of a specific CLI command (e.g., `--frontend list`, `--create-tool`). Catches `ValueError` and general `Exception` during agent execution to log errors and exit cleanly.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- None

**Module Dependencies:**
- **Standard/External:** `argparse`, `os`, `sys`, `subprocess`, `pathlib`, `uuid`, `traceback`, `re`, `json`, `qrcode` (optional).
- **Internal:** [AgentSessionManager](/ai/agents/session_manager.md), [BrainHub](/ai/modules/server/brain_hub.md), [ProcessManager](/ai/services/process_manager.md), [ModelConfigManager](/ai/model_config_manager.md), [ProgramConfig](/ai/config.md), [ModelType](/ai/entities/model_enums.md), [AgentOrchestrator](/ai/agents/agent.md), [LLMConnector](/ai/agents/agent.md), [ToolRegistry](/ai/agents/agent.md), [load_pipeline_config](/ai/agents/agent.md), [build_orchestrator](/ai/agents/agent.md), [Program](/ai/program.md), [DirectoryManager](/ai/services/directory_manager.md), [load_and_register_user_tools](/ai/tools/tool_loader.md), [ai.functions](/ai/functions.md), [ChatRoles](/ai/chat/chat.md), [BaseModel](/ai/core/llms/base_llm.md), [Color](/ai/color.md), [ask](/ai/direct.md), [read_piped_stdin](/ai/stdin_reader.md).