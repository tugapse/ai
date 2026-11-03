## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **model_enums** | [src/ai/entities/model_enums.py](/AgentDocs/ai/entities/model_enums.md) |

This component provides a centralized collection of enumeration types used to categorize and identify various aspects of the AI ecosystem within the application. It serves as a single source of truth for defining supported LLM engines, model architectures, and hardware inference backends.

By using these enums, the system ensures type safety and consistency across different modules, such as the [engine_manager](/AgentDocs/ai/services/engine_manager.md), [model_orchestrator](/AgentDocs/ai/services/model_orchestrator.md), and various model implementations like [ollama_model](/AgentDocs/ai/core/llms/ollama_model.md) or [gemini](/AgentDocs/ai/core/llms/gemini.md). It acts as a foundational data model layer that prevents string-based errors when routing requests to specific computational backends or model types.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `EngineType` | Enum | Defines supported LLM execution engines, including `HUGGINGFACE`, `OLLAMA`, `GGUF`, `VOICE_ENGINE`, `VECTOR_MEMORY`, `GEMINI_API`, `GEMINI_VERTEX`, `SERVER`, and `CLIENT`. |
| `ModelType` | Enum | Defines architectural types of models, such as `CAUSAL_LM`, `SEQ2SEQ_LM`, `OLLAMA`, `GGUF`, `GEMINI`, `OPEN_AI`, and `JARVIS`. Includes custom `__str__` and `__repr__` implementations. |
| `InferenceBackend` | Enum | Defines the hardware computational backends: `GPU_CUDA` (cuda), `GPU_AMD` (amd), and `CPU` (cpu). |

## 3. Implementation Details & Side Effects
Structural definitions only; no complex logic or side effects. The `ModelType` enum implements custom string representation logic:
- `__str__`: Returns the underlying string value of the enum member.
- `__repr__`: Returns the name of the enum member.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** 
    - `enum.Enum`
- **Internal:** 
    No internal imports present in this file.