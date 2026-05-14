## 1. Architectural Role

**Functional Mission**
The **BrainHub** class serves as the central intelligence controller and state manager for the system's Large Language Model (LLM) lifecycle. Its primary mission is to orchestrate the loading, unloading, and hot-swapping of AI models while simultaneously managing the persistence and retrieval of conversational history (memory) via JSON-based session files.

**System Context & Integration**
**BrainHub** acts as the bridge between high-level API requests and low-level model execution. It utilizes [ModelOrchestrator](/docs/services/model_orchestrator.md) to manage the physical presence of models in VRAM and relies on [HistoryManager](/docs/services/history_manager.md) logic (implemented via internal JSON methods) to maintain session continuity. It provides the necessary interface for [ServerModule](/docs/modules/server/server_module.md) to request specific "brains" (models) and retrieve real-time telemetry regarding token usage and context window saturation.

## 2. Environment & Configuration
**Environment Lookups:**
- `ProgramConfig.get(ProgramSetting.PATHS_MODEL_CONFIGS)`  Retrieves the directory path containing available model JSON configurations.

**Hardcoded Constants:**
- No hardcoded constants identified.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `__init__` | Class Method | Initializes the orchestrator, default history, and configuration state. |
| `new_history` | Method | Generates a standardized dictionary structure for new chat sessions. |
| `route_memory` | Method | Performs a "hot-swap" of the active session by updating file paths and reloading JSON data. |
| `add_history_message` | Method | Appends a role/content pair to the current history and triggers an immediate disk save. |
| `load_history_from_json` | Method | Deserializes session data from disk with validation for dictionary and list integrity. |
| `save_history_to_json` | Method | Serializes the current `self.history` state to a specified JSON file. |
| `get_timestamp` | Method | Generates an ISO-formatted string for temporal tracking of history updates. |
| `get_brain` | Method | The primary entry point for model acquisition; handles model swapping, system prompt updates, and VRAM management. |
| `unload_brain` | Method | Explicitly triggers the model's `unload()` method to free GPU resources. |
| `list_available_models` | Method | Scans the configured model directory to return a list of available model identifiers. |
| `get_stats` | Method | Aggregates token usage metrics (prompt, total, output) and context window percentage. |

## 4. Execution Logic & Flow
- **Initialization**: The component instantiates a `ModelOrchestrator`, sets an empty `history_file` string, and initializes a default history object using `new_history`.
- **Data Path (Memory)**: 
    - `route_memory` (Input: `session_filepath`) $\rightarrow$ `new_history` (State Reset) $\rightarrow$ `load_history_from_json` (Disk Read) $\rightarrow$ `self.history` (Updated State).
    - `add_history_message` (Input: `role`, `content`) $\rightarrow$ `append` to `self.history["messages"]` $\rightarrow$ `get_timestamp` $\rightarrow$ `save_history_to_json` (Disk Write).
- **Data Path (Inference Request)**:
    - `get_brain` (Input: `model_id`, `system_prompt`) $\rightarrow$ Check `current_model_id` $\rightarrow$ If mismatch: `unload_brain()` $\rightarrow$ If `orchestrator.llm` is null: `orchestrator.load()` $\rightarrow$ Return `llm` instance.
- **Conditional Branching**:
    - **JSON Validation**: In `load_history_from_json`, the system checks if the file exists, if it is a valid dictionary, and if the `messages` key contains a list. If any check fails, it resets the history to a clean state to prevent runtime crashes.
    - **Model Hot-Swapping**: In `get_brain`, if the requested `model_id` differs from the `current_model_id`, the system executes an unload sequence to prevent VRAM overflow before loading the new model.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `json`, `typing.Optional`, `datetime.datetime`
- **Internal Modules**: 
    - [functions](/docs/functions.md)
    - [ProgramConfig](/docs/config.md)
    - [ProgramSetting](/docs/config.md)
    - [HistoryManager](/docs/services/history_manager.md)
    - [ModelOrchestrator](/docs/services/model_orchestrator.md)
- **External Packages**: None identified.