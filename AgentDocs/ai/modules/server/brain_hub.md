## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **BrainHub** | [src/ai/modules/server/brain_hub.py](/src/ai/modules/server/brain_hub.py) |

The `BrainHub` class serves as the central coordination engine for the AI server module. It is responsible for managing the lifecycle of Large Language Models (LLMs), handling session-based conversation history, and maintaining the state of the active "brain" (the currently loaded model).

By acting as a mediator between the [ModelOrchestrator](/AgentDocs/ai/services/model_orchestrator.md) and the persistent storage mechanisms, it ensures that model swapping is handled safely (freeing GPU resources) and that conversation context is correctly loaded from or saved to JSON-based history files. It functions as a high-level controller within the server architecture, bridging the gap between raw model execution and session management.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `BrainHub(config: ProgramConfig)` | Class | Initializes the hub with global configuration, setting up the orchestrator and default history. |
| `new_history(session_title: Optional[str], session_id: str, session_folder: Optional[str])` | Method | Returns a fresh dictionary structure representing a new session state. |
| `route_memory(session_filepath: str, session_title: Optional[str], session_id: str, session_folder: Optional[str])` | Method | Performs a "hot-swap" of the active session by loading a specific JSON history file. |
| `add_history_message(role: str, content: str)` | Method | Appends a new message to the in-memory history and persists the update to the filesystem. |
| `load_history_from_json(filepath: str)` | Method | Reads a JSON file and populates the current history state with validation. |
| `save_history_to_json(filepath: str)` | Method | Serializes the current in-memory history state to a JSON file. |
| `get_timestamp()` | Method | Returns the current system time in ISO format. |
| `get_brain(model_id: str, system_prompt: str, model_config_data: Optional[dict] = None)` | Method | Manages model loading/unloading. Returns the active LLM instance, swapping models if the requested `model_id` differs from the current one. |
| `unload_brain()` | Method | Explicitly unloads the current LLM from the orchestrator to clear GPU memory. |
| `list_available_models()` | Method | Scans the configuration directory for available `.json` model definitions. |
| `get_stats()` | Method | Retrieves real-time token usage and context window statistics from the active model. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The component manages state transitions for both the conversation (history) and the hardware (LLM loading). When `get_brain` is called, it performs a check: if a different model is active, it calls `unload_brain` to prevent memory overflow before loading the new model via the `ModelOrchestrator`. History management uses a dictionary-based structure that is synchronized with the filesystem via `json` serialization.
- **Side Effects:** 
    - **Filesystem:** Reads and writes JSON files to disk for session history and model configurations.
    - **Hardware/GPU:** Triggers model loading and unloading processes which significantly impact GPU VRAM usage.
    - **Logging:** Uses `ai.functions.log` to record state changes, errors, and model swaps.
- **Error Handling:** 
    - If a history file is missing, corrupted (invalid JSON), or has an incorrect schema (missing `messages` list), the component logs a warning/error and resets the in-memory history to a "fresh" state rather than crashing.
    - Model loading errors are delegated to the `ModelOrchestrator`.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- `ProgramConfig`  Used to retrieve system paths and settings via `ProgramSetting`.

**Module Dependencies:**
- **Standard/External:** `os`, `typing`, `json`, `datetime`.
- **Internal:**
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ai.config](/AgentDocs/ai/config.md)
    - [ai.services.history_manager](/AgentDocs/ai/services/history_manager.md)
    - [ai.services.model_orchestrator](/AgentDocs/ai/services/model_orchestrator.md)