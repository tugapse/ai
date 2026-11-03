## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **BrainHub** | [src/ai/modules/server/brain_hub.py](/AgentDocs/ai/modules/server/brain_hub.py) |

The `BrainHub` class serves as the central coordination engine for the AI's cognitive operations within the server module. It is responsible for managing the lifecycle of Large Language Models (LLMs), handling session-based memory persistence, and maintaining the active state of the "brain" during user interactions.

By acting as a high-level controller, it bridges the gap between model orchestration and history management. It ensures that model swaps are handled gracefully (including GPU resource management via unloading) and that conversation history is consistently synchronized between in-memory structures and persistent JSON storage.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `BrainHub(config: ProgramConfig)` | Class | Initializes the hub with global configuration, setting up the `ModelOrchestrator` and default history. |
| `new_history(session_title: Optional[str], session_id: str, session_folder: Optional[str])` | Method | Returns a new dictionary structure representing a fresh session state. |
| `route_memory(session_filepath: str, session_title: Optional[str], session_id: str, session_folder: Optional[str])` | Method | Hot-swaps the active session context by loading a specific JSON file into memory. |
| `add_history_message(role: str, content: str)` | Method | Appends a message to the current history and immediately persists the change to disk. |
| `load_history_from_json(filepath: str)` | Method | Loads and validates a JSON file, populating the current history state or resetting it on failure. |
| `save_history_to_json(filepath: str)` | Method | Serializes the current in-memory history to a JSON file. |
| `get_timestamp()` | Method | Returns a current ISO-formatted timestamp string. |
| `get_brain(model_id: str, system_prompt: str, model_config_data: Optional[dict] = None)` | Method | Manages model loading/swapping. Returns the active LLM instance from the orchestrator. |
| `unload_brain()` | Method | Explicitly unloads the current model to free up system/GPU resources. |
| `list_available_models()` | Method | Scans the configuration directory for available model JSON files. |
| `get_stats()` | Method | Returns usage metrics (tokens, context window, usage percentage) for the active model. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The component utilizes a state-machine approach to model management. When `get_brain` is called with a different `model_id` than the `current_model_id`, it triggers an `unload_brain` sequence to prevent memory overflow before loading the new model via the `ModelOrchestrator`. History management is handled via dictionary manipulation and JSON serialization.
- **Side Effects:** 
    - **Filesystem:** Reads and writes JSON files for session history and model configurations.
    - **Hardware:** Interacts with GPU/System memory through model loading and unloading via the orchestrator.
    - **Logging:** Extensive use of `func.log` for tracking model swaps, memory loads, and errors.
- **Error Handling:** 
    - Implements validation for JSON structure during loading; if a file is corrupted or lacks the required `messages` key, it resets the history to a clean state rather than crashing.
    - Uses `try-except` blocks for `json.JSONDecodeError` to handle corrupted session files.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- Uses `ProgramConfig` to retrieve system paths, specifically for model configuration directories via `ProgramSetting.PATHS_MODEL_CONFIGS`.

**Module Dependencies:**
- **Standard/External:** `os`, `typing`, `json`, `datetime`.
- **Internal:**
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ai.config](/AgentDocs/ai/config.md)
    - [ai.services.history_manager](/AgentDocs/ai/services/history_manager.md)
    - [ai.services.model_orchestrator](/AgentDocs/ai/services/model_orchestrator.md)