## 1. Architectural Role
The `ollama_model.py` file implements an LLM bot using the Ollama library, providing methods for chatting, listing models, and pulling models.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `OllamaModel` | Class | Manages interactions with the Ollama LLM, including chatting, listing models, and pulling models. |
| `join_generation_thread` | Method | Clears the stop event for generation. |
| `chat` | Method | Handles the chat process with users, supporting streaming and non-streaming responses. |
| `list` | Method | Lists available models. |
| `pull` | Method | Pulls a model from the Ollama server. |

## 3. Execution Logic & Flow
- **Initialization**: The `OllamaModel` class is initialized with parameters such as `model_name`, `system_prompt`, `host`, `keep_alive`, and `model_params`. It sets up the Ollama client and pulls the specified model.
- **Data Path**: 
  - **Input**: Messages and optionally images.
  - **Processing**: 
    - Checks the system prompt.
    - Loads images if provided.
    - Clears the stop generation event.
    - Calls the Ollama client's `chat` method with the specified options.
  - **Output**: Yields or returns the chat response.
- **Conditional Branching**: 
  - Streaming vs. non-streaming responses.
  - Handling exceptions and interruptions.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `sys`, `threading`
- **Internal Modules**: `core.events`, `functions`
- **External Packages**: `ollama`, `tqdm`

## 5. Configuration & Environment
- **Hardcoded Constants**: `127.0.0.1` (default server IP)
- **Environment Lookups**: None