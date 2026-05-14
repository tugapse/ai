## 1. Architectural Role
Provides a specialized implementation of `BaseModel` for executing inference using GGUF-formatted models via the `llama-cpp-python` engine, optimized for CPU-bound environments.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `GGUFImageLLM` | Class | Main engine managing model lifecycle, memory locking, and inference execution. |
| `_null_log_callback` | Func | Provides a no-op callback to suppress `llama.cpp` C-level logging. |
| `_load_llm_params` | Method | Handles local cache verification, remote downloading via `hf_hub_download`, and model instantiation. |
| `_generate_in_thread` | Method | Internal worker for streaming inference, handling reasoning content and sentinel detection. |
| `_update_token_metrics` | Method | Calculates and updates `token_info_count` based on prompt and output lengths. |
| `get_message_tokens` | Method | Quantifies message list length using the `llama_model.tokenize` method. |
| `chat` | Method | Primary entry point for synchronous or asynchronous (streaming) text/image-based inference. |
| `list` | Method | Returns model metadata for registry identification. |
| `request_shutdown` | Method | Triggers controlled engine termination. |
| `unload` | Method | Releases `llama_model` memory, joins threads, and triggers garbage collection/CUDA cache clearing. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. Sets up C-level log suppression via `ctypes`.
    2. Initializes `_shared_mem_lock` and `error_queue`.
    3. Configures `token_info_count.max_context_window`.
    4. Invokes `_load_llm_params` to fetch/load the GGUF file.
    5. Instantiates the `Llama` object within a thread-safe lock.
- **Data Path**: 
    1. **Input**: `messages` (List[Dict]) + `images` (List) + `options` (Dict).
    2. **Preprocessing**: Deep copies messages $\rightarrow$ Integrates image content into user messages $\rightarrow$ Refreshes system prompt context $\rightarrow$ Estimates prompt token count.
    3. **Processing**: 
        - *Streaming*: Spawns `_generation_thread` $\rightarrow$ Iterates `llama_model.create_chat_completion` $\rightarrow$ Extracts `content` or `reasoning_content` $\rightarrow$ Passes content through `handle_sentinel`.
        - *Sync*: Executes `llama_model.create_chat_completion` $\rightarrow$ Parses tags via `parse_manual_tags`.
    4. **Output**: Yields tokens/dicts via `queue.Queue` or returns final text/action.
- **Conditional Branching**:
    1. **Model Availability**: Checks `self.llama_model` before chat; errors if `None`.
    2. **Local vs Remote**: `hf_hub_download` attempts `local_files_only=True` before falling back to `False`.
    3. **Inference Mode**: Branches between `stream=True` (thread-based queue) and `stream=False` (direct return).
    4. **Sentinel Detection**: `handle_sentinel` determines if the stream must terminate due to tool detection.
    5. **Reasoning Content**: Checks for `reasoning_content` key to route "thinking" text separately from standard content.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `threading`, `queue`, `gc`, `ctypes`, `json`, `typing`.
- **Internal Modules**: `core.llms.base_llm`, `functions`, `color`.
- **External Packages**: `huggingface_hub`, `llama_cpp`.

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `n_ctx` default: `4000`
    - `max_new_tokens` default: `2048`
    - `temperature` default: `0.7`
    - `top_p` default: `0.95`
    - `stop` sequences: `["System Response:", "User:"]`
- **Environment Lookups**: None explicitly via `os.getenv`; relies on `hf_hub_download` internal logic for cache locations.