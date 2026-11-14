## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| BaseLLM | ai/core/llms/base_llm |

This component defines the abstract foundation for all Language Model interactions within the system. Its primary responsibility is to manage the lifecycle of an LLM instance, including parameter configuration, context tracking, hardware detection, and providing standardized interfaces for both standard conversational and structured (JSON) generation tasks. It encapsulates core logic related to prompt formatting, system context injection, and managing asynchronous streaming operations.

This class serves as the abstract service layer for the LLM subsystem. It coordinates state across various specialized modules, such as tracking token usage via [TokenCountInfo](/ai/core/llms/base_llm.md) and managing external interactions through the [ToolRegistry](/ai/tools/tool_registry.md). It dictates the contract that concrete LLM implementations (e.g., specific backend integrations) must adhere to when executing inference.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| TokenCountInfo | Class | Tracks and calculates real-time token tracking metadata for inference context tracking. |
| ModelParams | Class | Encapsulates execution parameters, generation configurations, and sampler constraints for LLM requests. |
| BaseModel | Class | Abstract base class handling state management, context building, and tool interception logic for inference models. |
| BaseModel.create_message | Static Method | Constructs a structured message dictionary mapping role types to text payloads. |
| BaseModel.get_system_info | Method | Fetches host environment specs to pass down real-time OS and time data to system prompts. |
| BaseModel.check_system_prompt | Method | Ensures system metadata context sits atop history arrays, altering roles to fit prompt setups. |
| BaseModel.chat | Method | Abstract interface endpoint intended to process conversations and deliver textual streams. |
| BaseModel.generate_structured | Method | Abstract interface endpoint intended to force generation streams to follow rigid structural JSON parameters. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The `BaseModel` manages state via initialization (`__init__`), configuration loading (`_load_llm_params`), and context enrichment (`check_system_prompt`). It utilizes threading (`_generation_thread`) for asynchronous streaming. The `handle_sentinel` method implements complex stream interception logic to parse structured tool calls from incoming text chunks. Token tracking is managed by `TokenCountInfo`.
- **Side Effects:** The code interacts with external state by checking for PyTorch CUDA availability (`init_pytorch_cuda`), which affects `self.inference_device`. It uses `gc.collect()` and potentially `torch.cuda.empty_cache()` for memory management. It uses `threading.Event` and `threading.Thread` for asynchronous operations.
- **Error Handling:** It raises `NotImplementedError` in abstract methods (`chat`, `generate_structured`) if a subclass fails to implement them. It also handles `ImportError` when checking for PyTorch availability.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `os`, `gc`, `threading`, `typing`
- **Internal:** [ProgramConfig](/ai/config.md), [ProgramSetting](/ai/config.md), [functions](/ai/functions.md), [InferenceBackend](/ai/entities/model_enums.md), [ToolRegistry](/ai/tools/tool_registry.md)