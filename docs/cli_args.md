## 1. Architectural Role
Acts as the primary command-line entry point and execution dispatcher, translating CLI arguments into specific operational modes: Server (Brain), Client (Body), Agent (Pipeline), or Direct (One-shot).

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `CliArgs` | Class | Orchestrates argument parsing and dispatches execution to specialized handlers. |
| `parse_args` | Method | The central dispatcher that evaluates arguments to determine the system mode. |
| `_handle_create_tool` | Method | Generates a Python skeleton file for new user-defined tools. |
| `_handle_server_mode` | Method | Initializes and starts the `JarvisServerModule` for remote hosting. |
| `_handle_client_mode` | Method | Replaces the local LLM instance with a `RemoteBrainConnector`. |
| `_handle_local_direct_mode` | Method | Prepares context (files, folders, images) for non-agentic, direct interaction. |
| `_handle_agent_mode` | Method | Executes the `MessageOrchestrator` loop using a specified pipeline and tool registry. |
| `_handle_config_generation` | Method | Automates the creation of JSON model configuration files. |
| `_is_print_chat` | Method | Loads and displays historical chat logs via `ConsoleChatReader`. |
| `_is_install` | Method | Triggers the external `install_engines.py` script. |
| `_is_list_models` | Method | Placeholder for listing available model configurations. |
| `_has_output_files` | Method | Configures file writing parameters for the output. |
| `_has_folder` | Method | Loads all files within a directory into the chat context. |
| `_has_file` | Method | Loads specific file contents into the chat context. |
| `_has_image` | Method | Appends image paths to the chat's image buffer. |
| `_has_task_file` | Method | Injects a task file's content as a `SYSTEM` role message. |
| `_has_task` | Method | Loads a predefined task template from the user tasks directory. |
| `_has_message` | Method | Finalizes context and triggers the `ask` function for direct execution. |

## 3. Execution Logic & Flow
- **Initialization**: The `CliArgs` instance is instantiated; it does not hold internal state but relies on the `prog` object passed during method calls to manipulate the global program state.
- **Data Path**: 
    1. **Input**: CLI strings via `argparse`.
    2. **Processing**: `parse_args` identifies the mode $\rightarrow$ specific `_handle_*` method modifies `prog` (e.g., `prog.llm`, `prog.chat`, `prog.write_to_file`) $\rightarrow$ context is loaded (files/images/tasks).
    3. **Output**: Execution of `server.start()`, `orchestrator.run_loop()`, or `ask()`.
- **Conditional Branching**:
    - **System Commands**: If `create_tool`, `generate_config`, `install`, `print_chat`, or `list_models` are present, the process executes and exits immediately.
    - **Mode Priority**: 
        1. `args.server` $\rightarrow$ Server Mode $\rightarrow$ `os._exit(0)`.
        2. `args.remote` $\rightarrow$ Client Mode (modifies `prog.llm`) $\rightarrow$ continues to Local/Agent logic.
        3. `args.agent` $\rightarrow$ Agent Mode $\rightarrow$ `os._exit(0)`.
        4. Default $\rightarrow$ Local/Direct Mode $\rightarrow$ `_has_message` $\rightarrow$ `ask()`.

## 4. Resource Dependencies
- **Standard Libraries**: `argparse`, `os`, `sys`, `uuid`, `traceback`, `re`, `pathlib`.
- **Internal Modules**: `modules.server.brain_hub`, `model_config_manager`, `config`, `entities.model_enums`, `chat.chat`, `core.llms.base_llm`, `color`, `direct`, `agents.agent`, `tools.tool_loader`, `tools.agent_tools`, `functions`, `modules.client.remote_connector`, `modules.server.server_module`, `extras.console`.
- **External Packages**: None explicitly imported (relies on internal abstractions).

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - Default Server Host: `"0.0.0.0"`
    - Default Server Port: `9999`
    - Default Pipeline: `"pipelines/pipeline.json"`
- **Environment Lookups**:
    - `prog.config.get("SERVER_HOST")`
    - `prog.config.get("SERVER_PORT")`
    - `prog.config.get(ProgramSetting.PATHS_MODEL_CONFIGS)`
    - `prog.config.get(ProgramSetting.PATHS_TASKS_TEMPLATES)`