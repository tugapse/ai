## 1. Architectural Role
The `BrainHub` class acts as a lifecycle manager for Large Language Models, coordinating the loading, swapping, and unloading of model instances via a `ModelOrchestrator` to optimize VRAM usage.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `BrainHub` | Class | Manages the active state and switching of LLM "brains". |
| `__init__` | Method | Initializes the hub with a `ProgramConfig` and instantiates a `ModelOrchestrator`. |
| `get_brain` | Method | Validates the active model; triggers a swap/load sequence if the requested `model_id` differs from `current_model_id`. |
| `unload_brain` | Method | Signals the active LLM to shut down and clears the `orchestrator.llm` reference to free memory. |
| `list_available_models` | Method | Scans the filesystem for `.json` configuration files in the model config directory. |
| `get_stats` | Method | Aggregates token usage and context window metrics from the active LLM's `token_info_count`. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. Receives `ProgramConfig`.
    2. Instantiates `ModelOrchestrator`.
    3. Sets `current_model_id` to `None`.
- **Data Path (Model Acquisition)**: 
    `model_id` + `system_prompt` $\rightarrow$ `get_brain()` $\rightarrow$ (Optional: `unload_brain()`) $\rightarrow$ `orchestrator.load()` $\rightarrow$ `orchestrator.llm` (Return).
- **Conditional Branching**:
    - **Swap Logic**: If `current_model_id` exists AND does not match requested `model_id`, `unload_brain()` is called.
    - **Load Logic**: If `orchestrator.llm` is `None`, the orchestrator loads the model and updates `current_model_id`.
    - **Stats Logic**: If `orchestrator.llm` is `None`, returns `{"active": False}`; otherwise, calculates `usage_percent` based on `prompt_count` and `max_context_window`.

## 4. Resource Dependencies
- **Standard Libraries**: `os`
- **Internal Modules**: `functions` (as `func`), `services.model_orchestratrator.ModelOrchestrator`, `config.ProgramConfig`, `config.ProgramSetting`

## 5. Configuration & Environment
- **Hardcoded Constants**: None.
- **Environment Lookups**: 
    - `ProgramSetting.PATHS_MODEL_CONFIGS`: Used to locate the directory containing model JSON files.