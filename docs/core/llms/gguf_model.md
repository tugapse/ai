## 1. Architectural Role
Implements a CPU-hardened LLM engine using the GGUF format via `llama-cpp-python`, providing both synchronous and threaded streaming chat completions with integrated HuggingFace hub model resolution.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `GGUFImageLLM` | Class | Main engine class inheriting from `BaseModel` for GGUF model lifecycle and inference. |
| `GGUFImageLLM.__init__` | Method | Initializes model configuration, context window, and triggers model loading. |
| `GGUFImageLLM._load_llm_params` | Method | Resolves model path via `hf_hub_download` (local cache first, then remote) and instantiates `Llama`. |
| `GGUFImageLLM.chat` | Method | Primary entry point for inference; handles image injection, system prompt validation, and toggles between sync/stream modes. |
| `GGUFImageLLM._generate_in_thread` | Method | Manages the `llama_model.create_chat_completion` stream in a background thread, pushing tokens to a queue. |
| `GGUFImageLLM.get_message_tokens` | Method | Calculates token length of a message list using the model's internal tokenizer. |
| `GGUFImageLLM._update_token_metrics` | Method | Updates `token_info_count` with prompt and output token statistics. |
| `GGUFImageLLM.list` | Method | Returns a list containing the model name and type (`GGUF_STABLE`). |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. Calls `BaseModel` constructor.
    2. Sets `n_ctx` and initializes `error_queue`.
    3. Parses `model_params` into a dictionary (defaulting to `max_new_tokens: 2048`, `temperature: 0.7`).
    4. Executes `_load_llm_params`.
- **Data Path (Inference)**:
    1. **Input**: `messages` list, optional `images`, and `options`.
    2. **Preprocessing**: Images are converted via `load_images` and appended to the last user message; system prompts are validated via `check_system_prompt`.
    3. **Execution Branch**:
        - **Streaming**: Spawns `_generate_in_thread` $\rightarrow$ `llama_model.create_chat_completion(stream=True)` $\rightarrow$ `output_queue` $\rightarrow$ `yield` tokens.
        - **Synchronous**: Calls `llama_model.create_chat_completion(stream=False)` $\rightarrow$ returns full text.
    4. **Post-processing**: Updates `token_info_count` metrics and triggers `STREAMING_FINISHED_EVENT`.
- **Conditional Branching**:
    - **Model Loading**: If `hf_hub_download(local_files_only=True)` fails, it attempts a remote download.
    - **Tokenization**: If `llama_model.tokenize` fails, it falls back to a character-based estimation (`len // 4`).
    - **Generation Stop**: The `_generate_in_thread` loop monitors `stop_generation_event` to terminate early.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `threading`, `queue`, `gc`, `ctypes`
- **Internal Modules**: `core.llms.base_llm` (`BaseModel`, `ModelParams`), `functions`, `color` (`Color`)
- **External Packages**: `huggingface_hub` (`hf_hub_download`), `llama_cpp` (`Llama`, `llama_log_set`)

## 5. Configuration & Environment
- **Hardcoded Constants**:
    - `max_new_tokens`: 2048 (Default)
    - `temperature`: 0.7 (Default)
    - `top_p`: 0.95 (Default)
    - `n_ctx`: 4000 (Default)
- **Environment Lookups**: None.