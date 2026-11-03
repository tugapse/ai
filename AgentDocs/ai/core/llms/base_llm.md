## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **Base LLM Module** | [src/ai/core/llms/base_llm.py](/AgentDocs/ai/core/llms/base_llm.md) |

The `base_llm.py` module provides the foundational abstraction layer for all Large Language Model (LLM) implementations within the system. It defines the standardized interfaces, state management protocols, and lifecycle hooks required to integrate diverse inference backendsranging from local PyTorch/CUDA models to remote API-based servicesinto a unified execution framework.

This component serves as the core architectural template for the LLM subsystem. It is responsible for managing conversation history, constructing system prompts with real-time environmental context, handling token usage telemetry, and implementing a sentinel-based interception mechanism for tool calls. By providing a consistent `BaseModel` interface, it enables higher-level orchestrators to interact with various models without concern for specific backend implementation details.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `TokenCountInfo` | Class | Tracks and calculates real-time token usage metadata, including prompt counts and context window percentages. |
| `ModelParams` | Class | Encapsulates generation configurations such as temperature, top_p, top_k, and context window constraints. |
| `BaseModel` | Class | The abstract base class for all LLM implementations. Defines methods for chat, structured generation, and resource management. |
| `BaseModel.chat()` | Method | Abstract method to process conversations and return textual streams or full responses. |
| `BaseModel.generate_structured()` | Method | Abstract method to force model output to conform to a specific JSON schema. |
| `BaseModel.unload()` | Method | Abstract method to purge model allocations from hardware (VRAM/RAM). |
| `BaseModel.create_message()` | Static Method | Utility to construct structured message dictionaries (role/content). |

## 3. Implementation Details & Side Effects
- **Core Logic:** 
    - **Context Building:** The `check_system_prompt` and `_prepare_input` methods handle the transformation of raw message lists into model-ready formats, supporting both standard chat templates and legacy text-based concatenation.
    - **Tool Interception:** The `handle_sentinel` method implements a streaming interceptor that monitors incoming text chunks for specific trigger prefixes (e.g., `, `____`, `<|`) to detect and parse agent tool calls via the `ToolRegistry`.
    - **Hardware Management:** The `init_pytorch_cuda` and `clean_cache` methods manage the transition between CPU and GPU backends and handle memory flushing.
- **Side Effects:** 
    - **Memory Management:** Calls `gc.collect()` and `torch.cuda.empty_cache()` to manipulate system and VRAM availability.
    - **Logging:** Utilizes `functions.log` to report hardware detection and system status.
    - **Threading:** Uses `threading.Event` and background threads to manage non-blocking generation streams.
- **Error Handling:** 
    - Raises `ValueError` if a tokenizer is accessed before being defined.
    - Raises `NotImplementedError` in `BaseModel` for methods that must be overridden by subclasses.
    - Raises `RuntimeError` if a subclass fails to implement the required `unload` logic.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- `ProgramConfig.get_current().get(ProgramSetting.HIL_TOOLS)`  Retrieves the list of Human-In-The-Loop (HIL) tools from the global configuration.

**Module Dependencies:**
- **Standard/External:** `os`, `gc`, `threading`, `typing`, `torch` (optional, for CUDA support).
- **Internal:**
    - [ai.config](/AgentDocs/ai/config.md)
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ai.entities.model_enums](/AgentDocs/ai/entities/model_enums.md)
    - [ai.tools.tool_registry](/AgentDocs/ai/tools/tool_registry.md)