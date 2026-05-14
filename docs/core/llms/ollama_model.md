## 1. Architectural Role
`OllamaModel` serves as a concrete implementation of the LLM abstraction layer, specifically designed to interface with local or remote Ollama API servers. It extends [base_llm.md](core/llms/base_llm.md) to provide specialized capabilities including model pulling with real-time progress visualization via `tqdm`, synchronous and streaming chat interfaces, and automated model availability verification. It acts as a bridge between the system's core LLM orchestration and the Ollama service via the `ollama` client.

## 2. Environment & Configuration
**Environment Lookups:**
- `host` (via `__init__`)  Specifies the IP address/hostname of the Ollama server (defaults to `127.0.0.1`).

**Hardcoded Constants:**
- `server_ip` (Default: `"127.0.0.1"`)  Fallback address for the Ollama service.
- `":latest"` (Default: `":latest"`)  Appended to model names if no tag is specified during a pull operation.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `OllamaModel` | Class | Orchestrates interaction with the Ollama API, managing model lifecycle and inference. |
| `join_generation_thread` | Method | Resets the `stop_generation_event` to simulate thread joining for a synchronous process. |
| `chat` | Method | Executes model inference. Supports streaming (generator) or non-streaming (string) responses, image inputs, and custom options. |
| `list` | Method | Retrieves a list of available models from the Ollama server. |
| `pull` | Method | Checks if a specific model exists locally; if not, triggers the download process. |
| `__pull_model` | Method | Private helper that handles the iterative downloading of model layers with `tqdm` progress bars. |

## 4. Execution Logic & Flow
- **Initialization**:
    1. Calls `BaseModel` constructor.
    2. Establishes connection via `ollama.Client` using the provided `host`.
    3. Invokes `pull()` to ensure the requested `model_name` is available locally.
    4. Configures `keep_alive` and `options` (derived from `ModelParams`).
- **Data Path (Inference)**:
    1. **Input**: `messages` (list), `images` (list of paths), `stream` (bool), `options` (dict).
    2. **Processing**:
        - Merges default `options` with call-specific `options`.
        - Injects system prompts via `check_system_prompt`.
        - Loads and appends images if provided.
        - Clears `stop_generation_event`.
    3. **Output**: 
        - If `stream=True`: Yields text chunks iteratively until completion or `stop_generation_event` is set.
        - If `stream=False`: Returns the full text content string.
- **Conditional Branching**:
    - **Model Existence**: In `pull()`, if the model string contains no `:`, it is appended with `:latest`. If the model is found in `model.list()`, the pull process is aborted.
    - **Streaming Mode**: `chat()` branches logic based on the `stream` boolean, utilizing either a generator loop or a direct return.
    - **Interruption**: `chat()` monitors `stop_generation_event` during stream iteration to allow early exit.

## 5. Resource Dependencies
- **Standard Libraries**: `sys`, `threading`
- **Internal Modules**: 
    - [base_llm.md](core/llms/base_llm.md)
    - [events.md](core/events.md)
    - [functions.md](functions.md)
- **External Packages**: `ollama`, `tqdm`