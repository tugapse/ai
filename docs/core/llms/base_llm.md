## 1. Architectural Role
Defines the abstract base class and supporting data structures for all Large Language Model implementations, providing standardized tool-calling protocols, token usage tracking, and system prompt management.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `TokenCountInfo` | Class | Tracks and calculates real-time token usage metrics and context window saturation. |
| `BaseModel` | Class | Abstract base providing core logic for tool schema generation, sentinel-based stream interception, and system prompt enrichment. |
| `BaseModel._parse_docstring_to_schema` | Static Method | Converts Python function docstrings into JSON schemas for LLM tool consumption. |
| `BaseModel.format_tools_for_prompt` | Static Method | Generates a structured "System Access Manual" string containing tool definitions and calling protocols. |
| `BaseModel.parse_manual_tags` | Method | Uses regex to extract and sanitize tool call identifiers and JSON arguments from text streams. |
| `BaseModel.handle_sentinel` | Method | Manages stateful buffering of incoming text chunks to detect and intercept tool-calling triggers. |
| `BaseModel.init_pytorch_cuda` | Method | Attempts to initialize and verify CUDA availability for GPU acceleration. |
| `BaseModel._prepare_input` | Method | Transforms message lists into model-specific input tensors using tokenizers and chat templates. |
| `BaseModel.check_system_prompt` | Method | Enriches message history with system context and handles user-template overrides. |
| `BaseModel.chat` | Abstract Method | Interface for executing conversational inference. |
| `BaseModel.generate_structured` | Abstract Method | Interface for executing schema-constrained inference. |
| `BaseModel.unload` | Abstract Method | Interface for releasing model-specific memory and hardware resources. |
| `ModelParams` | Class | Data container for hyperparameter configuration (temperature, top_p, context window, etc.). |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. `BaseModel` instance is created with `model_name`, `system_prompt`, and `tool_registry`.
    2. `TokenCountInfo` is instantiated to track usage.
    3. `threading.Event` is initialized for generation control.
    4. `inference_device` defaults to `InferenceBackend.CPU`.
- **Data Path**: 
    1. **Input**: `messages` (list of dicts) $\rightarrow$ `check_system_prompt` (enrichment) $\rightarrow$ `_prepare_input` (tokenization) $\rightarrow$ Model-specific implementation.
    2. **Interception**: Raw stream chunk $\rightarrow$ `handle_sentinel` (buffering) $\rightarrow$ `parse_manual_tags` (regex/JSON parsing) $\rightarrow$ Tool Call Action.
    3. **Output**: `TokenCountInfo` updates `prompt_count` and `total_prompt_count` based on model feedback.
- **Conditional Branching**:
    - `handle_sentinel`: Determines if the current state is `is_intercepting` (buffering) or passing through.
    - `_prepare_input`: Checks for `apply_chat_template` availability to decide between template-based or manual string formatting.
    - `parse_manual_tags`: Uses regex to identify if a string contains J.A.R.V.I.S. or Gemma-style tool triggers.
    - `is_gpu_available`: Validates `inference_device` against actual hardware availability via `torch.cuda.is_available()`.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `gc`, `threading`, `json`, `re`, `typing`
- **Internal Modules**: `functions`, `entities.model_enums`, `tools.tool_registry`
- **External Packages**: `torch` (optional, via `import`)

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `CONTEXT_WINDO_...` range (2048 to 2097152)
    - `HIL_TOOLS`: `["execute_command", "write_file", "patch_file", "delete_file"]`
    - `TRIGGER_PREFIXES`: `["____", "<|"]`
- **Environment Lookups**: None (relies on `InferenceBackend` enum and `torch` detection).