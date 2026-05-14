## 1. Architectural Role
`ModelConfigManager` serves as the centralized persistence and factory layer for model-specific configuration schemas. It abstracts the complexities of generating, serializing, and deserializing JSON-based configuration profiles for different model architectures, ensuring that parameters for [core/llms/ollama_model.md](core/llms/ollama_model.md), [core/llms/gguf_model.md](core/llms/gguf_model.md), and [core/llms/huggingface_model.md](core/llms/huggingface_model.md) (Causal LM) are standardized and correctly structured before being consumed by the orchestration services.

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `n_gpu_layers` (Default: `-1`)  GGUF specific: utilizes all available GPU layers.
- `n_ctx` (Default: `8192`)  GGUF specific: context window size.
- `max_new_tokens` (Default: `4096` / `8192`)  Varies by type: limits generation length.
- `temperature` (Default: `0.3` / `0.8`)  Varies by type: controls randomness.
- `top_p` (Default: `0.95`)  Nucleus sampling threshold.
- `top_k` (Default: `50` / `30`)  Top-K sampling threshold.
- `presence_penalty` (Default: `1.1`)  Penalty for repeating tokens.
- `frequency_penalty` (Default: `1.2` / `1.1`)  Penalty for frequent tokens.
- `quantization_bits` (Default: `4`)  Causal LM specific: bit-depth for quantization.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ModelConfigManager` | Class | Static utility class for model configuration lifecycle management. |
| `generate_default_config` | Static Method | Orchestrates the creation of a default configuration dict based on `ModelType`. |
| `load_config` | Static Method | Reads and parses a JSON file into a dictionary with error handling. |
| `save_config` | Static Method | Serializes a dictionary to a JSON file with indentation. |
| `_generate_gguf_config` | Private Method | Constructs the schema specifically for GGUF models. |
| `_generate_causal_lm_config` | Private Method | Constructs the schema specifically for Causal LM (HuggingFace) models. |
| `_generate_ollama_config` | Private Method | Constructs the schema specifically for Ollama models. |

## 4. Execution Logic & Flow
- **Initialization**: Class is utilized via static methods; no instance state is maintained.
- **Data Path**:
    - **Generation**: `model_name` + `ModelType` $\rightarrow$ `generate_default_config` $\rightarrow$ specific `_generate_*_config` logic $\rightarrow$ Configuration Dictionary.
    - **Loading**: Filepath $\rightarrow$ `os.path.exists` check $\rightarrow$ `json.load` $\rightarrow$ Dictionary.
    - **Saving**: Dictionary $\rightarrow$ `json.dump` $\rightarrow$ File System.
- **Conditional Branching**:
    - `generate_default_config` branches logic based on the `ModelType` enum value to select the appropriate private generation method.
    - `load_config` implements error branching for `FileNotFoundError`, `JSONDecodeError`, and general `Exception`.

## 5. Resource Dependencies
- **Standard Libraries**: `json`, `os`, `sys`, `argparse`
- **Internal Modules**: 
    - [entities/model_enums.md](entities/model_enums.md)
    - [color.md](color.md)
    - [functions.md](functions.md)
- **External Packages**: None identified.