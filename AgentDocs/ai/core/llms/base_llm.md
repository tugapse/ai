## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **Base LLM Framework** | [src/ai/core/llms/base_llm.py](/src/ai/core/llms/base_llm.py) |

The `base_llm.py` module provides the foundational abstraction layer for all Large Language Model (LLM) integrations within the system. It defines the standard interface, state management protocols, and lifecycle hooks required to implement diverse inference backends, ranging from local GGUF models to remote API-based services.

Its primary responsibility is to standardize how the application interacts with models, handling complex tasks such as token usage tracking, system prompt enrichment, conversation template application, and tool call interception during streaming. By providing an abstract `BaseModel` class, it ensures that higher-level services can interact with any model implementation through a consistent API, regardless of the underlying hardware or provider.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `TokenCountInfo` | Class | Tracks real-time token metadata, including prompt counts, context window usage, and output tokens. |
| `ModelParams` | Class | Encapsulates generation configurations (e.g., temperature, top_p, max_new_tokens) and provides dictionary serialization. |
| `BaseModel` | Class | The abstract base class for all LLM implementations. Defines lifecycle methods, event handling, and input preparation. |
| `BaseModel.chat()` | Method | Abstract interface for processing conversations and returning textual responses or streams. |
| `BaseModel.generate_structured()` | Method | Abstract interface for forcing model output to conform to a specific JSON schema. |
| `BaseModel.unload()` | Method | Abstract interface for purging model resources from hardware (VRAM/RAM). |
| `BaseModel.create_message()` | Static Method | Utility to construct structured message dictionaries with `role` and `content`. |

## 3. Implementation Details & Side Effects
- **Core Logic:** 
    - **Context Management:** The `check_system_prompt` method dynamically injects system-level metadata (time, OS) and handles role-remapping if `override_system_by_user_template` is enabled.
    - **Streaming Interception:** `handle_sentinel` implements a stateful buffer mechanism to detect specific syntax markers (e.g., `, `____` or `<|`) within streamed chunks, allowing the system to intercept and parse tool calls via the `ToolRegistry`.
    - **Input Preparation:** `_prepare_input` utilizes tokenizer chat templates if available; otherwise, it falls back to a manual string formatting loop.
- **Side Effects:**
    - **Hardware Interaction:** `init_pytorch_cuda` and `clean_cache` interact with GPU drivers and VRAM via `torch`.
    - **Memory Management:** Explicitly invokes `gc.collect()` and `torch.cuda.empty_cache()` to manage hardware resources.
    - **Threading:** Uses `threading.Event` to signal and manage background generation threads.
- **Error Handling:** 
    - Throws `ValueError` if a tokenizer is accessed before being defined.
    - Throws `NotImplementedError` for abstract methods in `BaseModel`.
    - Throws `RuntimeError` if a subclass fails to implement the required `unload` method.

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