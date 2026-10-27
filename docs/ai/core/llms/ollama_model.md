## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | OllamaModel |
| Source file | ollama_model.py |

The **OllamaModel** class serves as a specialized implementation of the Large Language Model interface, specifically designed to interface with local LLM instances running via the Ollama service. It acts as a bridge between the high-level orchestration logic of the AI system and the local Ollama API, providing capabilities for model management (pulling/listing) and conversational interaction.

**Functional Mission**
The primary responsibility of **OllamaModel** is to abstract the complexities of the Ollama API, providing a standardized way to execute chat completions, manage model lifecycles (ensuring models are pulled before use), and handle streaming responses. It solves the problem of local model integration by wrapping the `ollama` Python library into the system's unified LLM architecture.

**System Context & Integration**
This component is a concrete implementation of [BaseModel](/docs/ai/core/llms/base_llm.md). It is utilized by higher-level services, such as the [Model Orchestrator](/docs/ai/services/model_orchestrator.md), to perform actual text generation. It handles the transition of raw message lists into Ollama-compatible formats, manages image injection for multimodal tasks, and provides a mechanism to interrupt generation via a stop event.

- **INTERNAL REFERENCES**: [BaseModel](/docs/ai/core/llms/base_llm.md), [ModelParams](/docs/ai/core/llms/base_llm.md), [func](/docs/ai/functions.md).

## 2. Environment & Configuration
**Environment Lookups:**
- `host` (via `__init__`)  Specifies the IP address/hostname of the Ollama server (defaults to `127.0.0.1`).

**Hardcoded Constants:**
- `server_ip` (Default: `"127.0.0.1"`)  The default local address for the Ollama service.
- `model_tag` (Default: `":latest"`)  Appended to model names if no specific tag is provided during a pull operation.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `OllamaModel` | Class | The main implementation of the Ollama-based LLM interface. |
| `__init__` | Method | Initializes the Ollama client, pulls the required model, and configures parameters. |
| `join_generation_thread` | Method | Clears the stop event to simulate thread joining (since Ollama streaming is synchronous). |
| `chat` | Method | Executes chat completions; supports both streaming (generator) and non-streaming (string) modes. |
| `list` | Method | Returns a list of models available on the Ollama server. |
| `pull` | Method | Checks if a model exists locally; if not, initiates a download via `__pull_model`. |
| `__pull_model` | Method | Private method that handles the logic of downloading a model with a `tqdm` progress bar. |

## 4. Execution Logic & Flow
- **Initialization**: 
    1. Calls `super().__init__` to set up base model properties.
    2. Initializes `ollama.Client` using the provided `host`.
    3. Executes `self.pull(self.model_name)` to ensure the model is available.
    4. Configures `keep_alive` and `options` (derived from `ModelParams`).
- **Data Path (Chat)**:
    1. **Input**: `messages` (list), `images` (list of strings), `stream` (bool), `options` (dict).
    2. **Processing**: 
        - Merges user-provided `options` with default `self.options`.
        - Injects system prompts via `check_system_prompt`.
        - Appends image data using `super().load_images` if images are present.
    3. **Execution**:
        - **If Streaming**: Iterates through the `ollama.chat` generator, yielding content chunks and checking `stop_generation_event` at each step.
        - **If Non-Streaming**: Executes a single call and returns the content string.
    4. **Output**: A generator of strings (streaming) or a single string (non-streaming).
- **Conditional Branching**:
    - **Model Existence**: In `pull()`, the code iterates through `self.model.list()` to check if the requested model is already present before attempting a download.
    - **Error Handling**: 
        - `KeyboardInterrupt` is caught during streaming to attempt a clean closure of the response.
        - General `Exception` triggers a critical error log and `sys.exit(1)`.
    - **Streaming Interruption**: If `self.stop_generation_event.is_set()` is true during a stream, the loop breaks and the response is closed.

## 5. Resource Dependencies
- **Standard Libraries**: `sys`, `traceback`
- **Internal Modules**: 
    - [BaseModel](/docs/ai/core/llms/base_llm.md)
    - [ModelParams](/docs/ai/core/llms/base_llm.md)
    - [func](/docs/ai/functions.md)
- **External Packages**: `ollama`, `tqdm`