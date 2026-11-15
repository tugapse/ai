## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| GGUFImageLLM | /ai/core/llms/gguf_model.md |

This component provides the core engine for running Large Language Models (LLMs) utilizing the GGUF format via `llama-cpp` bindings. Its primary responsibility is managing the entire lifecycle of a GGUF model: downloading the necessary files, loading the model weights into memory, executing inference (both synchronously and via streaming), and safely unloading resources. It is specifically designed to handle multimodal inputs by integrating vision projectors when available.

This class acts as a concrete implementation of the `BaseModel` interface, serving as a specialized LLM service layer within the application architecture. It abstracts the low-level details of `llama.cpp` operations, allowing the higher-level Orchestrator to interact with the model via a standardized `chat` method, while coordinating with services like [ai.functions](/ai/functions.md) and [ai.core.llms.base_llm.BaseModel](/ai/core/llms/base_llm.md).

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| `GGUFImageLLM` | Class | Implements the LLM interface using llama-cpp bindings for GGUF models, handling loading, inference, and resource management. |
| `GGUFImageLLM.chat` | Method | Returns a token generator when streaming is True, or the full response otherwise. Accepts messages, optional images, and generation options. |
| `GGUFImageLLM.list` | Method | Returns a list describing the models this instance can handle. |
| `GGUFImageLLM.request_shutdown` | Method | Initiates a controlled shutdown sequence for the model. |
| `GGUFImageLLM.unload` | Method | Frees the llama.cpp model and associated GPU/CPU resources safely. |
| `GGUFImageLLM.image_to_data_url` | Static Method | Converts various image inputs (file path, PIL image, or data URL) into a standardized data URL string. |
| `GGUFImageLLM.load_images` | Method | Converts a list of raw images into the specific OpenAI-style content structure required for vision models. |
| `GGUFImageLLM._attach_images` | Method | Modifies the last user message in a message history to incorporate image parts into the content structure. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The model loading process first attempts to download the GGUF file via [huggingface_hub.hf_hub_download](/huggingface_hub.py). It then initializes the `llama.cpp` Llama object within a shared memory lock. Inference is executed either synchronously (`_sync_chat`) or via a dedicated thread (`_generate_in_thread`) which streams results back through a queue. A critical feature is the GPU headroom check (`_check_gpu_headroom`) which proactively aborts the load if insufficient GPU memory is available for generation.
- **Side Effects:**
    - Network: Downloads model files from Hugging Face Hub.
    - Filesystem: Reads model files from the local Hugging Face cache.
    - Global State: Mutates the internal state (`self.llama_model`, `self.stop_generation_event`, `self.token_info_count`) and interacts with global GPU memory via `torch.cuda.empty_cache()` during unloading.
    - Threads: Spawns a background thread for streaming inference.
- **Error Handling:** Catches `GpuMemoryError` during loading, which is used to signal to the caller that the GPU is too constrained, allowing for retries with fewer layers. General loading exceptions are caught, and if they do not match known GPU OOM markers, a `RuntimeError` is raised. Streaming errors are caught within the thread, and the generation process terminates gracefully.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `sys`, `threading`, `queue`, `gc`, `ctypes`, `collections`, `typing`, `huggingface_hub`, `llama_cpp`, `torch` (conditional).
- **Internal:** [ai.functions](/ai/functions.md), [ai.core.llms.base_llm.BaseModel](/ai/core/llms/base_llm.md), [ai.core.llms.load_errors.GpuMemoryError](/ai/core/llms/load_errors.md), [ai.color.Color](/ai/color.md), [ai.tools.tool_registry.ToolRegistry](/ai/tools/tool_registry.md), [ai.services.gpu_advisor.nvidia_snapshot](/ai/services/gpu_advisor.md).