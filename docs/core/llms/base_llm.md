## 1. Architectural Role
Provides a standardized abstract base class and parameter schema to enforce a consistent interface for all Large Language Model (LLM) implementations, handling common tasks like system prompt enrichment, token tracking, and hardware acceleration checks.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `TokenCountInfo` | Class | Tracks prompt, total, and output token counts and generates a formatted usage string. |
| `BaseModel` | Class | Abstract base defining the LLM lifecycle, input preparation, and event triggering. |
| `BaseModel.init_pytorch_cuda` | Method | Detects CUDA availability and updates `inference_device`. |
| `BaseModel._prepare_input` | Method | Formats chat messages into model-specific strings or tensors using `apply_chat_template` or manual formatting. |
| `BaseModel.add_event` | Method | Registers callback listeners for specific event names. |
| `BaseModel.trigger` | Method | Executes all registered listeners for a given event. |
| `BaseModel.create_message` | Static Method | Standardizes message creation into `{'role': role, 'content': content}` dictionaries. |
| `BaseModel.get_system_info` | Method | Retrieves concise system context (Time, OS, PWD) via `functions`. |
| `BaseModel.check_system_prompt` | Method | Injects system context and the `system_prompt` into the message history, optionally masking the system role as 'user'. |
| `BaseModel.join_generation_thread` | Method | Manages the termination and cleanup of background generation threads. |
| `BaseModel.chat` | Method | Abstract method for generating responses (must be implemented by subclasses). |
| `BaseModel.list` | Method | Abstract method for listing available models. |
| `BaseModel.pull` | Method | Abstract method for downloading model weights. |
| `BaseModel.is_gpu_available` | Method | Validates if the current `inference_device` is functional. |
| `BaseModel.clean_cache` | Method | Triggers `torch.cuda.empty_cache()` and `gc.collect()`. |
| `BaseModel.getTokenCount` | Method | Returns the `TokenCountInfo` instance. |
| `BaseModel.request_shutdown` | Method | Orchestrates a graceful stop of generation, thread joining, and cache clearing. |
| `ModelParams` | Class | Data container for LLM hyperparameters (temperature, top_p, etc.) with a `to_dict` export. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. `BaseModel` instance is created with `model_name` and `system_prompt`.
    2. `TokenCountInfo` is initialized to track usage.
    3. `stop_generation_event` (threading.Event) is created for interruption handling.
    4. `inference_device` defaults to `InferenceBackend.CPU`.
- **Data Path (Input Processing)**:
    1. `check_system_prompt` $\rightarrow$ Fetches system info $\rightarrow$ Prepends system prompt $\rightarrow$ Filters existing system messages $\rightarrow$ Returns updated message list.
    2. `_prepare_input` $\rightarrow$ Checks for `tokenizer.apply_chat_template` $\rightarrow$ (If exists) generates prompt $\rightarrow$ (If not) manually concatenates "System:", "User:", and "Assistant:" labels $\rightarrow$ Tokenizes result into tensors.
- **Conditional Branching**:
    - **Hardware Detection**: `init_pytorch_cuda` branches based on `torch.cuda.is_available()`.
    - **Template Logic**: `_prepare_input` branches based on whether the tokenizer supports `apply_chat_template`.
    - **Role Masking**: `check_system_prompt` branches based on `override_system_by_user_template` to change "system" roles to "user".
    - **GPU Validation**: `is_gpu_available` branches based on `InferenceBackend` enum value (CUDA vs AMD).

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `gc`, `threading`
- **Internal Modules**: `functions`, `entities.model_enums.InferenceBackend`
- **External Packages**: `torch` (Optional/Lazy-loaded)

## 5. Configuration & Environment
- **Hardcoded Constants**:
    - `CONTEXT_WINDOW_SMALL`: 2048
    - `CONTEXT_WINDOW_MEDIUM`: 4096
    - `CONTEXT_WINDOW_LARGE`: 8192
    - `CONTEXT_WINDOW_XLARGE`: 16384
    - `CONTEXT_WINDOW_HUGE`: 32768
    - `CONTEXT_WINDOW_GIANT`: 65536
    - `STREAMING_FINISHED_EVENT`: "streaming_finished"
- **Environment Lookups**: `os.getcwd()` used within `get_system_info`.