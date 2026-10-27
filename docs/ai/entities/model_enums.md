## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | model_enums |
| Source file | model_enums.py |

The **model_enums** component serves as the centralized type-definition authority for the entire AI ecosystem. By providing strictly typed enumerations, it ensures that disparate modulesranging from low-level inference engines to high-level orchestration servicescommunicate using a unified vocabulary, preventing string-based errors and logic mismatches.

**Functional Mission**
The primary responsibility of **model_enums** is to define the categorical boundaries for engine types, model architectures, and hardware backends. It solves the problem of configuration ambiguity by providing a single source of truth for valid system states, such as identifying whether a model is running via [Ollama](/docs/ai/core/llms/ollama_model.md) or a [HuggingFace](/docs/ai/core/llms/huggingface_model.md) pipeline.

**System Context & Integration**
This component acts as a foundational dependency for almost all high-level logic. It is consumed by the [Engine Manager](/docs/ai/services/engine_manager.md) to instantiate correct drivers, by the [Model Orchestrator](/docs/ai/services/model_orchestrator.md) to route requests to the appropriate [LLM Connector](/docs/ai/agents/llm_connector.md), and by the [Model Config Manager](/docs/ai/model_config_manager.md) to validate user-provided settings. It facilitates the transition from abstract user intent to concrete hardware execution by mapping high-level model types to specific [Inference Backend](/docs/ai/core/llms/base_llm.md) requirements.

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `EngineType.HUGGINGFACE` (Default: `"huggingface"`)  Identifier for HuggingFace integration.
- `EngineType.OLLAMA` (Default: `"ollama"`)  Identifier for Ollama integration.
- `EngineType.GGUF` (Default: `"gguf"`)  Identifier for GGUF quantized models.
- `EngineType.VOICE_ENGINE` (Default: `"voice_engine"`)  Identifier for voice processing modules.
- `EngineType.VECTOR_MEMORY` (Default: `"vector_memory"`)  Identifier for long-term memory modules.
- `EngineType.GEMINI_API` (Default: `"gemini_api"`)  Identifier for Google Gemini API.
- `EngineType.GEMINI_VERTEX` (Default: `"gemini_vertex"`)  Identifier for Google Gemini Vertex AI.
- `EngineType.SERVER` (Default: `"server_hub"`)  Identifier for server-side hub modules.
- `EngineType.CLIENT` (Default: `"client_link"`)  Identifier for client-side link modules.
- `ModelType.CAUSAL_LM` (Default: `"causal_lm"`)  Architecture type for decoder-only models.
- `ModelType.SEQ2SEQ_LM` (Default: `"seq2seq_lm"`)  Architecture type for encoder-decoder models.
- `ModelType.OLLAMA` (Default: `"ollama"`)  Model type served via Ollama.
- `ModelType.GGUF` (Default: `"gguf"`)  Model type for GGUF quantized files.
- `ModelType.GEMINI` (Default: `"gemini"`)  Model type for Google Gemini.
- `ModelType.OPEN_AI` (Default: `"openai"`)  Model type for OpenAI hosted models.
- `ModelType.JARVIS` (Default: `"jarvis"`)  Model type for the custom JARVIS implementation.
- `InferenceBackend.GPU_CUDA` (Default: `"cuda"`)  Hardware target for NVIDIA GPUs.
- `InferenceBackend.GPU_AMD` (Default: `"amd"`)  Hardware target for AMD GPUs.
- `InferenceBackend.CPU` (Default: `"cpu"`)  Hardware target for central processing units.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `EngineType` | Enum | Defines supported LLM engines and specialized modules (Voice, Memory, API). |
| `ModelType` | Enum | Defines architectural patterns and provider-specific model classifications. |
| `InferenceBackend` | Enum | Defines the hardware acceleration layer (CUDA, AMD, or CPU). |

## 4. Execution Logic & Flow
Direct exports or structural definitions only; no internal logic flow.

## 5. Resource Dependencies
- **Standard Libraries**: `enum`
- **Internal Modules**: 
    - No internal module imports identified.
- **External Packages**: No external packages identified.