## 1. Architectural Role
Implements a concrete LLM provider interface using the `ollama` library to facilitate model pulling, chat interactions (streaming and non-streaming), and lifecycle management for Ollama-hosted models.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `OllamaModel` | Class | Orchestrates connection, model availability, and inference via the Ollama API. |
| `join_generation_thread` | Method | Clears the `stop_generation_event` to simulate thread joining for synchronous streaming. |
| `chat` | Method | Executes model inference; handles message preparation, image loading, and stream/non-stream response logic. |
| `list` | Method | Returns a list of available models from the Ollama server. |
| `pull` | Method | Checks for model existence and triggers a download if the model is missing. |
| `__pull_model` | Method | Private; manages the iterative download process with `tqdm` progress bars per digest. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. Calls `super().__init__` with `model_name` and `system_prompt`.
    2. Sets `server_ip` (defaults to `127.0.0.1`).
    3. Instantiates `ollama.Client`.
    4. Executes `self.pull(self.model_name)` to ensure local availability.
    5. Stores `keep_alive` state and `options` (derived from `ModelParams`).
- **Data Path**:
    - **Input**: `messages` (list), `images` (list of strings), `stream` (bool), `options` (dict).
    - **Processing**: 
        1. Merges provided `options` with `self.options`.
        2. Passes `messages` through `check_system_prompt`.
        3. Appends processed images via `super().load_images`.
        4. Dispatches request to `self.model.chat`.
    - **Output**: 
        - If `stream=True`: Yields string chunks of content.
        - If `stream=False`: Returns a single string of content.
- **Conditional Branching**:
    - **Streaming vs. Non-Streaming**: `chat` branches based on the `stream` boolean to either yield chunks or return a direct response.
    - **Model Existence**: `pull` checks if `model_name` contains a colon (tag); if not, appends `:latest`.
    - **Digest Tracking**: `__pull_model` compares `current_digest` to existing `bars` to manage multiple concurrent download progress bars.
    - **Interruption Check**: During streaming, the loop checks `self.stop_generation_event.is_set()` to terminate the generator.

## 4. Resource Dependencies
- **Standard Libraries**: `sys`, `threading`
- **Internal Modules**: `core.events.Events`, `core.llms.base_llm.BaseModel`, `core.llms.base_llm.ModelParams`, `functions`
- **External Packages**: `ollama`, `tqdm`

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `127.0.0.1` (Default `server_ip`)
    - `:latest` (Default model tag suffix)
- **Environment Lookups**: None identified.