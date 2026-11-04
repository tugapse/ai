## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **OllamaModel** | [src/ai/core/llms/ollama_model.py](/src/ai/core/llms/ollama_model.py) |

The `OllamaModel` class provides a concrete implementation of a Large Language Model (LLM) interface specifically designed to interact with a local Ollama server. It abstracts the complexities of managing model lifecycles, including checking for model availability, pulling missing models from the Ollama registry, and handling both streaming and non-streaming chat completions.

This component serves as a specialized driver within the LLM provider layer of the application. It inherits from [BaseModel](/AgentDocs/ai/core/llms/base_llm.md) to ensure compatibility with the broader orchestration system, allowing the application to swap between different LLM backends (like OpenAI or HuggingFace) while maintaining a consistent API for conversational interaction and image processing.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `OllamaModel(...)` | Class | Initializes the model client, connects to the specified host, and ensures the requested model is pulled locally. |
| `join_generation_thread(timeout: float = 60.0)` | Method | Clears the internal stop event to simulate thread joining, as Ollama's streaming is handled synchronously. |
| `chat(messages: list, images: list[str] = None, stream: bool = True, options: object = {})` | Method | The primary interface for interaction. Supports streaming text chunks or returning a single string. Handles system prompts and image inputs. |
| `list()` | Method | Returns a dictionary containing the list of models currently available on the Ollama server. |
| `pull(model_name, stream=True)` | Method | Ensures a specific model is available on the local server, pulling it if necessary. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The class utilizes the `ollama` Python library to communicate with a local server. During the `chat` process, it merges user-provided options with default model parameters and processes image paths through the base class's loading mechanism. For streaming, it iterates over the generator provided by the Ollama client and monitors a `stop_generation_event` to allow for graceful interruption.
- **Side Effects:** 
    - **Network/IPC:** Communicates with a local or remote Ollama server via HTTP/API.
    - **Filesystem/Network:** The `pull` method triggers model downloads to the local machine.
    - **Console I/O:** Uses `tqdm` to render progress bars during model pulls and logs status updates via the `ai.functions` module.
- **Error Handling:** 
    - Catches `KeyboardInterrupt` during streaming to attempt a clean closure of the response stream.
    - Catches general `Exception` during generation and triggers a system exit with a traceback to prevent inconsistent application states during critical LLM communication failures.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- `host`  (Passed via constructor) The IP address/hostname of the Ollama server. Defaults to `127.0.0.1`.
- `keep_alive`  (Passed via constructor) Boolean determining if the model should remain loaded in the Ollama server memory.

**Module Dependencies:**
- **Standard/External:** `ollama`, `tqdm`, `sys`, `traceback`.
- **Internal:** 
    - [BaseModel](/AgentDocs/ai/core/llms/base_llm.md)
    - [ModelParams](/AgentDocs/ai/core/llms/base_llm.md)
    - [ai.functions](/AgentDocs/ai/functions.md)