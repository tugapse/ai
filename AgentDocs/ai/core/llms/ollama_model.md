## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **OllamaModel** | [src/ai/core/llms/ollama_model.py](/AgentDocs/ai/core/llms/ollama_model.md) |

The `OllamaModel` class provides a specialized implementation of a Large Language Model (LLM) interface designed specifically for interacting with local Ollama server instances. It abstracts the complexities of managing local model lifecycles, including checking for model existence, pulling missing models with progress visualization, and handling conversational streaming.

This component serves as a concrete implementation of the [BaseModel](/AgentDocs/ai/core/llms/base_llm.md) interface. It fits into the broader LLM orchestration layer of the application, allowing the system to utilize locally hosted models for inference, thereby reducing dependency on external cloud APIs and enhancing data privacy.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `OllamaModel` | Class | A model implementation that communicates with an Ollama server via the `ollama` Python library. |
| `join_generation_thread(timeout: float = 60.0)` | Method | Clears the stop event for the generation process. Note: Since Ollama's streaming is synchronous in this implementation, no actual thread joining occurs. |
| `chat(messages: list, images: list[str] = None, stream: bool = True, options: object = {})` | Method | Executes a chat session. If `stream` is `True`, it yields text chunks; otherwise, it returns the full string. Supports image inputs for multimodal models. |
| `list()` | Method | Retrieves a dictionary of all models currently available on the connected Ollama server. |
| `pull(model_name, stream=True)` | Method | Ensures the specified model is available locally by pulling it from the Ollama registry if it is missing. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The class manages model interaction through the `ollama.Client`. When `chat` is called, it processes the message history, integrates system prompts, and appends image data if provided. The `pull` mechanism includes a private `__pull_model` method that uses `tqdm` to provide a real-time visual progress bar for model downloads by tracking the `digest` and `completed` status in the stream.
- **Side Effects:** 
    - **Network:** Performs HTTP requests to the Ollama server (defaulting to `127.0.0.1`) for model listing, pulling, and inference.
    - **Console I/O:** Uses `tqdm` to render progress bars in the terminal during model pulls and uses `func.log`/`func.error` for status updates.
- **Error Handling:** 
    - Catches `KeyboardInterrupt` during streaming to attempt a clean closure of the response stream.
    - Catches general `Exception` during generation and calls `sys.exit(1)` after logging a critical error and printing the traceback.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No specific environment variables are explicitly parsed within this file, though the `host` parameter in the constructor determines the target server IP.

**Module Dependencies:**
- **Standard/External:** `ollama`, `tqdm`, `sys`, `traceback`.
- **Internal:** 
    - [BaseModel](/AgentDocs/ai/core/llms/base_llm.md)
    - [ModelParams](/AgentDocs/ai/core/llms/base_llm.md)
    - [func](/AgentDocs/ai/functions.md)