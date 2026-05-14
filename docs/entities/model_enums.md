## 1. Architectural Role
Acts as the centralized type-definition registry for the system, providing strictly typed enumerations that govern model selection, engine orchestration, and hardware acceleration strategies. It serves as the foundational schema used by [services/engine_manager.md](services/engine_manager.md) to validate engine types, [services/model_orchestrator.md](services/model_orchestrator.md) to categorize model architectures, and various model implementations like [core/llms/huggingface_model.md](core/llms/huggingface_model.md) or [core/llms/ollama_model.md](core/llms/ollama_model.md) to ensure compatibility with the underlying execution backends.

## 2. Environment & Configuration
**Environment Lookups:**
No environment lookups identified.

**Hardcoded Constants:**
- `EngineType.HUGGINGFACE` (Default: `"huggingface"`)  Identifier for HF integration.
- `EngineType.OLAMMA` (Default: `"ollama"`)  Identifier for Ollama local service.
- `EngineType.GGUF` (Default: `"gguf"`)  Identifier for quantized local models.
- `EngineType.VOICE_ENGINE` (Default: `"voice_engine"`)  Identifier for [modules/voice/vibe_module.md](modules/voice/vibe_module.md).
- `EngineType.VECTOR_MEMORY` (Default: `"vector_memory"`)  Identifier for [modules/memory/vector_memory_module.md](modules/memory/vector_memory_module.md).
- `EngineType.SERVER` (Default: `"server_hub"`)  Identifier for [modules/server/server_module.md](modules/server/server_module.md).
- `EngineType.CLIENT` (Default: `"client_link"`)  Identifier for [modules/client/remote_module.md](modules/client/remote_module.md).
- `ModelType.CAUSAL_LM` (Default: `"causal_lm"`)  Identifier for decoder-only architectures.
- `ModelType.SEQ2SEQ_LM` (Default: `"seq2seq_lm"`)  Identifier for encoder-decoder architectures.
- `InferenceBackend.GPU_CUDA` (Default: `"cuda"`)  Identifier for NVIDIA hardware acceleration.
- `InferenceBackend.GPU_AMD` (Default: `"amd"`)  Identifier for AMD hardware acceleration.
- `InferenceBackend.CPU` (Default: `"cpu"`)  Identifier for standard processor execution.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `EngineType` | Enum | Categorizes the operational engine/module responsible for processing (e.g., LLM, Voice, Memory, or Network Hubs). |
| `ModelType` | Enum | Defines the architectural nature of the model (e.g., Causal, Seq2Seq) or specific provider-based types (e.g., Gemini, OpenAI). |
| `InferenceBackend` | Enum | Specifies the hardware abstraction layer used for computation (CUDA, AMD, or CPU). |

## 4. Execution Logic & Flow
- **Initialization**: The module defines static Enum classes at import time, establishing the available type-space for the application.
- **Data Path**: No dynamic data path; serves as a static reference registry.
- **Conditional Branching**: 
    - `ModelType.__str__`: Returns the string `value` for human-readable output.
    - `ModelType.__repr__`: Returns the Enum `name` for developer-centric debugging/logging.

## 5. Resource Dependencies
- **Standard Libraries**: `enum`
- **Internal Modules**: None.
- **External Packages**: None.