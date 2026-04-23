## 1. Architectural Role
`OllamaModel` serves as a concrete implementation of `BaseModel` that interfaces with the Ollama API to manage local LLM lifecycle, model pulling, and text/image generation.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `OllamaModel` | Class | Orchestrates communication with the Ollama server for model management and inference. |
| `__init__` | Method | Initializes the Ollama client, sets server IP, configures model parameters, and ensures the target model is pulled. |
| `join_generation_thread` | Method | Resets the `stop_generation_event` (synchronous placeholder for the base class interface). |
| `chat` | Method | Handles message exchange with the LLM, supporting both streaming and non-streaming modes and image inputs. |
| `list` | Method | Retrieves a list of available models from the Ollama server. |
| `pull` | Method | Checks if a model exists locally; if not, triggers the `__pull_model` download process. |
| `__pull_model` | Method | Manages the streaming download of a model with real-time progress tracking via `tqdm`. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. Calls `super().__init__` to set basic model identity.
    2. Instantiates `ollama.Client` using `host` (default: "127.0.0.1").
    3. Executes `pull()` to ensure the specified `model_name` is available.
    4. Sets `keep_alive` status and initializes `options` from `ModelParams`.
- **Data Path (Chat)**: 
    1. **Input**: `messages` (list), `images` (list), `stream` (bool), `options` (dict).
    2. **Preprocessing**: Merges `self.options` with provided `options` $\rightarrow$ applies `check_system_prompt` $\rightarrow$ appends images via `load_images`.
    3. **Execution**: 
        - If `stream=True`: Iterates through `self.model.chat` generator $\rightarrow$ yields content $\rightarrow$ monitors `stop_generation_event` to break loop.
        - If `stream=False`: Calls `self.model.chat` $\rightarrow$ returns final content string.
    4. **Output**: Stream of content chunks or a single response string.
- **Conditional Branching**:
    - **Model Pulling**: If `model_name` lacks a tag, `:latest` is appended; if the model is already in `self.model.list()`, the download is skipped.
    - **Streaming Logic**: Diverges between a `yield` loop (with interruption checks) and a direct return based on the `stream` flag.
    - **Error Handling**: Catches `KeyboardInterrupt` for stream closure and generic `Exception` for critical failures (triggering `sys.exit(1)`).

## 4. Resource Dependencies
- **Standard Libraries**: `sys`, `threading`
- **Internal Modules**: `core.events.Events`, `core.llms.base_llm.BaseModel`, `core.llms.base_llm.ModelParams`, `functions`
- **External Packages**: `ollama`, `tqdm`

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - Default Host: `"127.0.0.1"`
    - Default Model Tag: `":latest"`
- **Environment Lookups**: None.