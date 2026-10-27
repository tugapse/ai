## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | BaseModel |
| Source file | base_llm.py |

The **BaseModel** serves as the foundational abstract layer for all Large Language Model (LLM) implementations within the system. It provides a standardized interface for managing model state, handling conversation history, and orchestrating the complexities of inference, such as token tracking, device management (CPU/GPU), and hardware-level memory cleanup.

**Functional Mission**
The primary responsibility of **BaseModel** is to abstract the specific implementation details of different inference backends (e.g., OpenAI, Ollama, HuggingFace) into a unified API. It solves the problem of heterogeneous model interfaces by providing consistent methods for chat, structured generation, and system prompt injection, while also managing the lifecycle of streaming data and tool interception.

**System Context & Integration**
This component acts as the parent class for all specialized LLM modules. It integrates deeply with [ToolRegistry](/docs/ai/tools/tool_registry.md) to intercept and parse agentic tool calls from streaming text. It utilizes [ProgramConfig](/docs/ai/config.md) to retrieve operational settings like Human-in-the-Loop (HIL) configurations. Downstream, it provides the necessary data structures and event triggers used by [ModelOrchestrator](/docs/ai/services/model_orchestrator.md) to manage multi-model workflows and [StreamOrchestrator](/docs/ai/services/stream_orchestrator.md) to handle real-time output delivery.

## 2. Environment & Configuration
**Environment Lookups:**
- `HIL_TOOLS` (via `ProgramConfig.get_current().get(ProgramSetting.HIL_TOOLS)`)  Retrieves settings for Human-in-the-Loop tool execution.

**Hardcoded Constants:**
- `CONTEXT_WINDOW_SMALL` (Default: `2048`)  Minimum context window size.
- `CONTEXT_WINDOW_MEDIUM` (Default: `4096`)  Standard context window size.
- `CONTEXT_WINDOW_LARGE` (Default: `8192`)  Large context window size.
- `CONTEXT_WINDOW_XLARGE` (Default: `16384`)  Extra-large context window size.
- `CONTEXT_WINDOW_HUGE` (Default: `32768`)  Huge context window size.
- `CONTEXT_WINDOW_GIANT` (Default: `65536`)  Giant context window size.
- `CONTEXT_WINDOW_128K` (Default: `128748`)  128K context window size.
- `CONTEXT_WINDOW_256K` (Default: `262144`)  256K context window size.
- `CONTEXT_WINDOW_1M` (Default: `1048576`)  1M context window size.
- `CONTEXT_WINDOW_2M` (Default: `2097152`)  2M context window size.
- `TRIGGER_PREFIXES` (Default: `["`["____", "<|"]`)  Syntax markers used to detect tool call boundaries in streams.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `TokenCountInfo` | Class | Tracks real-time token usage, prompt counts, and context window saturation. |
| `ModelParams` | Class | Encapsulates generation hyperparameters (temperature, top_p, etc.) for LLM requests. |
| `BaseModel` | Class | Abstract base class defining the lifecycle and interface for all LLM implementations. |
| `_load_llm_params` | Method | Initializes token tracking metadata based on model options. |
| `handle_sentinel` | Method | Monitors streaming chunks for syntax markers to intercept tool calls via `ToolRegistry`. |
| `init_pytorch_cuda` | Method | Detects CUDA availability to switch the `inference_device` to GPU. |
| `_prepare_input` | Method | Transforms message lists into tokenized tensors using chat templates or legacy formatting. |
| `add_event` | Method | Registers callback listeners for lifecycle hooks. |
| `trigger` | Method | Executes registered listeners for a specific event. |
| `check_system_prompt` | Method | Injects system context and OS metadata into the message history. |
| `clean_cache` | Method | Flushes VRAM (via PyTorch) and triggers Python garbage collection. |
| `request_shutdown` | Method | Signals generation threads to stop and performs resource cleanup. |
| `chat` | Method | Abstract endpoint for conversational text streaming. |
| `generate_structured` | Method | Abstract endpoint for constrained JSON schema generation. |
| `unload` | Method | Abstract endpoint for purging model resources from hardware. |

## 4. Execution Logic & Flow
- **Initialization**: 
    1. Sets model identity and system prompts.
    2. Initializes `TokenCountInfo` and `threading.Event` for stop signals.
    3. Fetches `HIL_TOOLS` from `ProgramConfig`.
    4. Sets default `inference_device` to `CPU`.
- **Data Path (Inference Preparation)**:
    1. `check_system_prompt` gathers OS/Time info via `functions.get_system_info_prompt_concise()`.
    2. `_prepare_input` checks for `tokenizer.apply_chat_template`.
    3. If template exists: Applies template $\rightarrow$ Tokenizes $\rightarrow$ Returns Tensors.
    4. If no template: Formats as `Role: Content` $\rightarrow$ Tokenizes $\rightarrow$ Returns Tensors.
- **Data Path (Streaming Interception)**:
    1. `handle_sentinel` receives a chunk and a buffer.
    2. If `is_intercepting` is `False`: Checks for `TRIGGER_PREFIXES`. If found, switches interception mode.
    3. If `is_intercepting` is `True`: Passes buffer to `ToolRegistry.parse_manual_tags`.
    4. If tags are parsed: Returns the action and clears the buffer.
- **Conditional Branching**:
    - **Hardware Detection**: `init_pytorch_cuda` branches between `InferenceBackend.GPU_CUDA` and `InferenceBackend.CPU` based on `torch.cuda.is_available()`.
    - **System Prompt Override**: If `override_system_by_user_template` is `True`, system messages are converted to `user` roles to satisfy specific model requirements.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `gc`, `threading`, `typing`
- **Internal Modules**: 
    - [ProgramConfig](/docs/ai/config.md)
    - [ProgramSetting](/docs/ai/config.md)
    - [functions](/docs/ai/functions.md)
    - [InferenceBackend](/docs/ai/entities/model_enums.md)
    - [ToolRegistry](/docs/ai/tools/tool_registry.md)
- **External Packages**: `torch` (optional, for CUDA/GPU support)