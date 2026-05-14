## 1. Architectural Role
`GGUFImageLLM` serves as a specialized inference engine designed for CPU-hardened execution of GGUF-formatted models via the `llama-cpp-python` binding. It implements the [base_llm.md](core/llms/base_llm.md) interface to provide streaming and synchronous chat capabilities, specifically handling reasoning content (e.g., DeepSeek/Gemma) and tool-call interception via a sentinel pattern. The class manages its own memory lifecycle, including model loading from the Hugging Face hub, thread-safe inference execution using a shared memory lock, and explicit resource unloading to prevent memory leaks in high-density environments.

## 2. Environment & Configuration
**Environment Lookups:**
- `model_repo_id` (via `__init__`)  Hugging Face repository identifier for model retrieval.
- `gguf_filename` (via `__init__`)  Specific filename of the GGUF model to download/load.

**Hardcoded Constants:**
- `n_ctx` (Default: `4000`)  Maximum context window size.
- `max_new_tokens` (Default: `2048`)  Limit for generated output tokens in `options`.
- `temperature` (Default: `0.7`)  Sampling temperature for stochasticity.
- `top_p` (Default: `0.95`)  Nucleus sampling threshold.
- `stop` (Default: `["System Response:", "User:"]`)  Token sequences that trigger generation termination.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `GGUFImageLLM` | Class | Primary implementation of the GGUF-based LLM interface. |
| `_load_llm_params` | Method | Handles local cache checks and remote downloading of GGUF files. |
| `_generate_in_thread` | Method | Orchestrates background streaming, reasoning extraction, and sentinel detection. |
| `get_message_tokens` | Method | Calculates token count of the message history using the llama model tokenizer. |
| `chat` | Method | Entry point for user queries; supports both streaming (generator) and synchronous (return value) modes. |
| `list` | Method | Returns model metadata for registry purposes. |
| `request_shutdown` | Method | Triggers the orchestrated teardown of the model instance. |
| `unload` | Method | Performs manual memory cleanup, including thread joining and `gc.collect()`. |

## 4. Execution Logic & Flow
- **Initialization**:
    1. Calls `super().__init__` to establish base properties.
    2. Configures `token_info_count` via [llm_params_configurator.md](core/llms/llm_params_configurator.md).
    3. Executes `_load_llm_params` to acquire the model file and initialize the `Llama` object under a `_shared_mem_lock`.
- **Data Path (Streaming)**:
    1. **Input**: `messages` (List[Dict]), `options` (dict).
    2. **Preprocessing**: Deep copies messages, appends image data if present, and refreshes system prompts.
    3. **Processing**: Spawns `_generation_thread` $\rightarrow$ calls `llama_model.create_chat_completion(stream=True)`.
    4. **Transformation**: Iterates through chunks $\rightarrow$ extracts `reasoning_content` (formatted via `color.md`) and `content` $\rightarrow$ runs `handle_sentinel` to detect tool calls.
    5. **Output**: Yields tokens/dictionaries to the caller via a `queue.Queue`.
- **Conditional Branching**:
    1. `if stream`: Diverts logic to a background thread and queue-based consumer loop.
    2. `if reasoning`: Intercepts reasoning tokens to provide specialized "Thinking" UI feedback.
    3. `if isinstance(out, dict)`: Validates if the output is a tool call to trigger `tool_detected` events.
    4. `if self.stop_generation_event.is_set()`: Allows external interruption of the generation loop.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `threading`, `queue`, `gc`, `ctypes`, `json`, `typing`.
- **Internal Modules**: 
    - [base_llm.md](core/llms/base_llm.md)
    - [llm_params_configurator.md](core/llms/llm_params_configurator.md)
    - [functions.md](functions.md)
    - [color.md](color.md)
- **External Packages**: `huggingface_hub`, `llama_cpp`, `torch` (optional, for CUDA cache clearing).