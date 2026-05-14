## 1. Architectural Role
Acts as the foundational abstract base class and utility provider for all Large Language Model implementations within the system. It defines the standardized interface for model interaction, implements the J.A.R.V.I.S. tool-calling protocol (including dynamic docstring-to-JSON schema translation), manages token usage telemetry via `TokenCountInfo`, and provides unified sentinel logic for intercepting streaming outputs to detect tool triggers. This file serves as the parent for specialized implementations like [core/llms/open_ai.md](core/llms/open_ai.md) and [core/llms/ollama_model.md](core/llms/ollama_model.md), ensuring consistent behavior across different inference backends.

## 2. Environment & Configuration
**Environment Lookups:**
- `inference_device` (via `__init__`)  Determines if the model utilizes `InferenceBackend.GPU_CUDA` or `InferenceBackend.CPU`.

**Hardcoded Constants:**
- `CONTEXT_WINDOW_SMALL` (Default: `2048`)  Minimum context capacity.
- `CONTEXT_WINDOW_MEDIUM` (Default: `4096`)  Standard context capacity.
- `CONTEXT_WINDOW_LARGE` (Default: `8192`)  High context capacity.
- `CONTEXT_WINDOW_XLARGE` (Default: `16384`)  Extended context capacity.
- `CONTEXT_WINDOW_HUGE` (Default: `32768`)  Massive context capacity.
- `CONTEXT_WINDOW_GIANT` (Default: `65536`)  Ultra-large context capacity.
- `CONTEXT_WINDOW_128K` (Default: `128748`)  128K token capacity.
- `CONTEXT_WINDOW_256K` (Default: `262144`)  256K token capacity.
- `CONTEXT_WINDOW_1M` (Default: `1048576`)  1M token capacity.
- `CONTEXT_WINDOW_2M` (Default: `2097152`)  2M token capacity.
- `HIL_TOOLS` (Default: `["execute_command", "write_file", "patch_file", "delete_file"]`)  List of tools requiring Human-In-The-Loop confirmation.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `TokenCountInfo` | Class | Tracks and calculates token usage percentages and log strings. |
| `BaseModel` | Class | Abstract base providing tool parsing, sentinel logic, and system prompt management. |
| `_parse_docstring_to_schema` | Static Method | Converts Python function docstrings into JSON schemas for LLM tool-use. |
| `format_tools_for_prompt` | Static Method | Generates the system instruction manual for available tools. |
| `parse_manual_tags` | Method | Extracts tool names and arguments from raw text streams using regex. |
| `handle_sentinel` | Method | Manages buffering of stream chunks to intercept tool-calling patterns. |
| `init_pytorch_cuda` | Method | Configures hardware acceleration if `torch` is available. |
| `_prepare_input` | Method | Formats message lists into model-specific input tensors/strings. |
| `check_system_prompt` | Method | Injects system context and handles user-override templates. |
| `chat` | Abstract Method | Primary entry point for model conversation (must be implemented). |
| `generate_structured` | Abstract Method | Entry point for constrained schema generation (must be implemented). |
| `unload` | Abstract Method | Resource cleanup routine (must be implemented). |
| `ModelParams` | Class | Data container for inference hyperparameters (temperature, top_p, etc.). |

## 4. Execution Logic & Flow
- **Initialization**: `BaseModel` initializes state including `stop_generation_event`, `inference_device`, and injects the `ToolRegistry` to enable tool-aware capabilities.
- **Data Path (Tool Generation)**: 
    1. `format_tools_for_prompt` scans `tool_registry`.
    2. `_parse_docstring_to_schema` extracts parameter metadata.
    3. The resulting string is injected into the model's system prompt.
- **Data Path (Inference Stream Interception)**: 
    1. `handle_sentinel` monitors incoming text chunks.
    2. If a trigger prefix (e.g., `____@tool`) is detected, it enters interception mode.
    3. `parse_manual_tags` attempts to regex-extract the tool name and JSON payload.
    4. JSON is cleaned (fixing quote artifacts/unquoted keys) and parsed.
    5. The tool execution dictionary is returned to the orchestrator.
- **Conditional Branching**: 
    - `is_gpu_available` checks the `inference_device` and `torch.cuda.is_available()` before attempting GPU operations.
    - `override_system_by_user_template` logic determines if system messages are re-labeled as `user` messages to bypass certain model constraints.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `gc`, `threading`, `json`, `re`, `typing`.
- **Internal Modules**: 
    - [functions](functions.md)
    - [entities/model_enums.md](entities/model_enums.md)
    - [tools/tool_registry.md](tools/tool_registry.md)
- **External Packages**: `torch` (optional, for CUDA/GPU support).