## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **model_enums** | [src/ai/entities/model_enums.py](/src/ai/entities/model_enums.py) |

This component provides a centralized set of enumeration types used to categorize and identify different types of Large Language Model (LLM) engines, model architectures, and hardware backends. It ensures type safety and consistency across the application when selecting or configuring AI models.

As a data model component, it serves as a foundational reference for various services and orchestrators. It is used by components such as [src/ai/services/engine_manager.md](/src/ai/services/engine_manager.md) to identify supported engines and [src/ai/services/model_orchestrator.md](/src/ai/services/model_orchestrator.md) to manage different model architectures and inference backends.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `EngineType` | Enum | Defines supported LLM engines, including providers like `HUGGINGFACE`, `OLLAMA`, `GEMINI_API`, and specialized modules like `VOICE_ENGINE` or `VECTOR_MEMORY`. |
| `ModelType` | Enum | Defines architectural categories for models, such as `CAUSAL_LM`, `SEQ2SEQ_LM`, `OLLAMA`, `GGUF`, `GEMINI`, `OPEN_AI`, and the custom `JARVIS`. Includes custom `__str__` and `__repr__` implementations. |
| `InferenceBackend` | Enum | Defines the computational hardware used for inference, specifically `GPU_CUDA`, `GPU_AMD`, and `CPU`. |

## 3. Implementation Details & Side Effects
Structural definitions only; no complex logic or side effects.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** 
    - `enum.Enum`
- **Internal:** 
    No internal dependencies.