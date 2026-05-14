## 1. Architectural Role
Acts as the central intelligence controller responsible for managing LLM lifecycle (loading/unloading), orchestrating model swaps to optimize VRAM, and maintaining conversational state through JSON-based history persistence.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `BrainHub` | Class | Primary controller for model orchestration and session memory. |
| `new_history` | Method | Generates a standardized dictionary structure for new chat sessions. |
| `route_memory` | Method | Re-routes the active session by updating file paths and reloading JSON state. |
| `add_history_message` | Method | Appends a role/content pair to the current history and triggers a disk save. |
| `load_history_from_json` | Method | Deserializes session data from disk with schema validation and error recovery. |
| `save_history_to_json` | Method | Serializes the current `self.history` dictionary to a physical JSON file. |
| `get_timestamp` | Method | Returns the current system time in ISO 8601 format. |
| `get_brain` | Method | Retrieves the active LLM instance, performing hot-swaps or system prompt updates if necessary. |
| `unload_brain` | Method | Explicitly releases GPU/VRAM resources by invoking the model's unload sequence. |
| `list_available_models` | Method | Scans the configured model directory to return a list of available model IDs. |
| `get_stats` | Method | Aggregates token usage, context window, and capacity metrics from the active model. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. Receives `ProgramConfig`.
    2. Instantiates `ModelOrchestrator`.
    3. Initializes `self.history` with a default structure via `new_history`.
    4. Sets `self.current_model_id` to `None`.
- **Data Path (Memory Management)**: 
    `session_filepath` (Input) $\rightarrow$ `route_memory` $\rightarrow$ `load_history_from_json` $\rightarrow$ `self.history` (Internal State) $\rightarrow$ `add_history_message` $\rightarrow$ `save_history_to_json` (Output).
- **Data Path (Inference Request)**: 
    `model_id` + `system_prompt` (Input) $\rightarrow$ `get_brain` $\rightarrow$ Check `current_model_id` $\rightarrow$ (If mismatch) `unload_brain` $\rightarrow$ `orchestrator.load` $\rightarrow$ `self.orchestrator.llm` (Output).
- **Conditional Branching**:
    - **Model Swap**: In `get_brain`, if `current_model_id` exists and differs from requested `model_id`, `unload_brain` is executed.
    - **Prompt Update**: In `get_brain`, if the model is already loaded but the `system_prompt` differs, the attribute is updated in-place.
    - **JSON Validation**: In `load_history_from_json`, checks if the file exists, is valid JSON, and contains the required `messages` list; failures trigger a "fresh start" state reset.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `typing.Optional`, `json`, `datetime.datetime`
- **Internal Modules**: `functions` (as `func`), `config` (`ProgramConfig`, `ProgramSetting`), `services.history_manager` (`HistoryManager`), `services.model_orchestrator` (`ModelOrchestrator`)

## 5. Configuration & Environment
- **Hardcoded Constants**: None.
- **Environment Lookups**: 
    - `self.config.get(ProgramSetting.PATHS_MODEL_CONFIGS)`: Used to locate the directory for available model JSONs.