## 1. Architectural Role
Handles the initialization and execution of the AI assistant's main program, including loading configurations, initializing components, and managing the chat loop.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `Program` | Class | Manages the lifecycle of the AI assistant, including loading configurations, initializing components, and handling the chat loop. |
| `load_config` | Method | Loads the main program configuration. |
| `init_program` | Method | Initializes components based on configuration and CLI arguments. |
| `init_model_params` | Method | Initializes model parameters. |
| `init` | Method | Initializes the core components of the program. |
| `read_system_file` | Method | Reads the system prompt file. |
| `process_token` | Method | Processes a token. |
| `clear_process_token` | Method | Clears the process token. |
| `output_requested` | Method | Handles when output is requested. |
| `_handle_tool_call` | Method | Handles a tool call. |
| `start_chat` | Method | Starts the chat loop. |
| `llm_stream_finished` | Method | Handles when the LLM stream finishes. |
| `run_agent_flow` | Method | Runs the agent flow. |
| `load_events` | Method | Loads events and binds callbacks. |
| `_load_model` | Method | Loads the model instance. |
| `_save_chat_history` | Method | Saves the chat history. |
| `cleanup` | Method | Cleans up resources. |
| `run` | Method | Main loop starting point. |

## 3. Execution Logic & Flow
- **Initialization**: The `Program` class is initialized, and the `load_config` method is called to load the main program configuration. The `init_program` method is then called to initialize components based on the configuration and CLI arguments.
- **Data Path**: The primary transformation of data occurs in the `start_chat` method, where the LLM's chat method is called with the current chat messages, and the output is processed and displayed.
- **Conditional Branching**: Key decision points include checking if the LLM is loaded, handling tool calls, and managing the state of the chat loop.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `re`, `sys`, `json`, `argparse`, `traceback`, `unicodedata`
- **Internal Modules**: `config`, `core`, `color`, `functions`, `services`, `extras`, `agents`
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: `__no_model__`, `__no_chat_name__`, `PRINT_MODE`, `TOKENS_PER_PRINT`, `THINKING_MODE`, `ENABLE_THINKING_DISPLAY`
- **Environment Lookups**: None