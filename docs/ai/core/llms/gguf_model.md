## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | GGUFImageLLM |
| Source file | gguf_model.py |

The **GGUFImageLLM** component serves as a specialized inference engine designed to execute Large Language Models in GGUF format, specifically optimized for CPU-bound environments. It acts as a high-performance bridge between the raw `llama-cpp-python` bindings and the high-level orchestration layers of the AI system, providing a hardened interface for local model execution.

**Functional Mission**
The primary responsibility of **GGUFImageLLM** is to manage the lifecycle of a GGUF-formatted model, including local cache verification via HuggingFace, memory-safe loading, streaming inference, and resource deallocation. It solves the problem of efficient local LLM execution by implementing thread-safe access to the model instance and providing structured handling for reasoning tokens and tool-call sentinels.

**System Context & Integration**
This component is a concrete implementation of the [BaseModel](/docs/ai/core/llms/base_llm.md) interface. It integrates deeply with the [ToolRegistry](/docs/ai/tools/tool_registry.md) to intercept and parse model-generated tool calls during the streaming process. It communicates state changes (such as streaming completion or tool detection) via the event system inherited from [BaseModel](/docs/ai/core/llms/base_llm.md). Data flows from the user through the [ModelOrchestrator](/docs/ai/services/model_orchestrator.md) into this engine, which then streams tokens back through a queue-based mechanism to ensure non-blocking UI/CLI updates.

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `n_ctx` (Default: `4000`)  The maximum context window size for the model.
- `max_new_tokens` (Default: `2048`)  The default limit for generated output tokens.
- `temperature` (Default: `0.7`)  The default sampling temperature.
- `top_p` (Default: `0.95`)  The default nucleus sampling parameter.
- `stop` (Default: `["