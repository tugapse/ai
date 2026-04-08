## 1. Architectural Role
Defines enumerations for different types of language model engines, architectural types of language models, and inference backends used by the application.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `EngineType` | Enum | Represents different types of LLM engines supported. |
| `ModelType` | Enum | Defines the architectural types of language models supported. |
| `InferenceBackend` | Enum | Specifies the inference backends available. |

## 3. Execution Logic & Flow
- **Initialization**: The file imports the `Enum` class from the `enum` module and defines three enumerations: `EngineType`, `ModelType`, and `InferenceBackend`.
- **Data Path**: No data transformation occurs. The enumerations are used to represent specific values.
- **Conditional Branching**: No conditional branching is present.

## 4. Resource Dependencies
- **Standard Libraries**: `enum`
- **Internal Modules**: None
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: `HUGGINGFACE`, `OLLA`, `GGUF`, `CAUSAL_LM`, `SEQ2SEQ_LM`, `OLLAMA`, `GGUF`, `GEMINI`, `OPEN_AI`, `GPU_CUDA`, `GPU_AMD`, `CPU`
- **Environment Lookups**: None