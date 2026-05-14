## 1. Architectural Role
[brain_hub.py](src/ai/modules/server/brain_hub.py) acts as the central intelligence controller and state manager for the server module. It orchestrates the lifecycle of Large Language Models (LLMs) via [model_orchestrator.md](services/model_orchestrator.md), manages conversational continuity by interfacing with [history_manager.md](services/history_manager.md), and handles the hot-swapping of model weights and system prompts to optimize VRAM utilization. It serves as the bridge between high-level API requests and the low-level model execution layer.

## 2. Environment & Configuration
**Environment Lookups:**
- `PATHS_MODEL_CONFIGS` (via `list_available_models` $\rightarrow$ `ProgramConfig`)  Locates the directory containing JSON model definitions.

**Hardcoded Constants:**
- `"default"` (Default: `"default"`)  Fallback session ID during initialization.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `BrainHub` | Class | Central coordinator for LLM lifecycle and session history. |
| `new_history` | Func | Generates a standardized dictionary schema for new chat sessions. |
| `route_memory` | Func | Updates active session file path and reloads history state. |
| `add_history_message` | Func | Appends a role/content pair to history and triggers a JSON save. |
| `load_history_from_json` | Func | Deserializes session data from disk with schema validation. |
| `save_history_to_json` | Func | Serializes current history dictionary to a physical JSON file. |
| `get_timestamp` | Func | Generates ISO-format strings for temporal tracking. |
| `get_brain` | Func | Manages model switching, prompt updates, and VRAM unloading. |
| `unload_brain` | Func | Explicitly releases LLM resources via the orchestrator. |
| `list_available_models` | Func | Returns a list of model identifiers available in the config path. |
| `get_stats` | Func | Aggregates token usage and context window telemetry. |

## 4. Execution Logic & Flow
- **Initialization**: Sets up `ModelOrchestrator`, initializes a default empty history object, and prepares the configuration context.
- **Data Path (Memory Management)**:
    1. `route_memory` receives path/metadata $\rightarrow$ 2. `new_history` resets local dict $\rightarrow$ 3. `load_history_from_json` reads disk $\rightarrow$ 4. `history` state updated.
- **Data Path (Message Persistence)**:
    1. `add_history_message` receives role/content $\rightarrow$ 2. Dict appended $\rightarrow$ 3. `get_timestamp` generates time $\rightarrow$ 4. `save_history_to_json` writes to disk.
- **Conditional Branching (Model Swapping)**:
    - **IF** `current_model_id` exists AND $\neq$ requested `model_id`:
        - Trigger `unload_brain()` to clear VRAM.
    - **IF** `orchestrator.llm` is already loaded with the correct ID:
        - **IF** `system_prompt` differs: Update `llm.system_prompt`.
        - Return active `llm`.
    - **ELSE**:
        - Execute `orchestratator.load(model_id, system_prompt)`.
        - Update `current_model_id`.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `json`, `typing`, `datetime`
- **Internal Modules**: 
    - [functions.md](functions.md)
    - [config.md](config.md)
    - [history_manager.md](services/history_manager.md)
    - [model_orchestrator.md](services/model_orchestrator.md)
- **External Packages**: None identified.