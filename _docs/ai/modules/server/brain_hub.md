## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| BrainHub | [brain_hub](/ai/modules/server/brain_hub.md) |

This component serves as the central orchestration hub for the entire AI system, managing the lifecycle of loaded language models and coordinating session history. Its primary responsibility is to ensure that the correct LLM is active, handle model swapping between different configurations, and manage concurrent access to the model to prevent race conditions during generation or agent execution.

As a core service component, `BrainHub` sits at the intersection of model management and persistent state. It interacts heavily with the [ModelOrchestrator](/ai/services/model_orchestrator.md) to load/unload models, the [HistoryManager](/ai/services/history_manager.md) for session persistence, and the [ProcessManager](/ai/services/process_manager.md) to broadcast its operational status.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| `ModelLease` | Class | Manages a single usage session of a loaded model, ensuring `_end_generation` is called upon release. |
| `BrainHub` | Class | Manages core AI state, model loading, and history. |
| `BrainHub.new_history` | Method | Initializes a fresh history structure dictionary for a new session. |
| `BrainHub.route_memory` | Method | Instructs the system to hot-swap the active session context by loading data from a specified file. |
| `BrainHub.add_history_message` | Method | Appends a message to the in-memory history and immediately persists the change to the active JSON file. |
| `BrainHub.load_history_from_json` | Method | Loads session data from a specific JSON file, handling validation and decoding errors. |
| `BrainHub.save_history_to_json` | Method | Persists the current in-memory history state to the specified JSON file. |
| `BrainHub.get_timestamp` | Method | Generates a standardized ISO format timestamp string. |
| `BrainHub.model_key` | Static Method | Converts a model name into its canonical, filesystem-friendly key used internally. |
| `BrainHub.agent_running` | Property | True if a dedicated web agent run is currently utilizing the model, blocking chat requests. |
| `BrainHub.busy` | Property | True if any chat generation (`_generations > 0`) or agent run is active. |
| `BrainHub.add_cancel_hook` | Method | Registers a callable function to be executed when a forced model swap is initiated. |
| `BrainHub.acquire` | Method | Loads the requested model (or verifies it is loaded) and returns a `ModelLease`, enforcing atomic acquisition. |
| `BrainHub.release_with` | Static Method | Creates a weak reference finalizer to automatically call `lease.release()` when the owner object is garbage collected. |
| `BrainHub.get_brain` | Method | The core method to ensure the requested model is loaded, handling swaps based on the `on_busy` policy. |
| `BrainHub.unload_brain` | Method | Explicitly unloads the currently active model from the orchestrator, freeing associated resources. |
| `BrainHub.list_model_configs` | Method | Retrieves a list of all known model configurations, including metadata like loadability and vision support. |
| `BrainHub.list_available_models` | Method | Returns a simple list of model keys that are currently loadable by the server. |
| `BrainHub.get_stats` | Method | Queries the active LLM for token usage statistics. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The `BrainHub` manages model state transitions using internal locks (`self._lock`) and condition variables (`self._idle`). Model acquisition (`acquire` / `get_brain`) implements a complex state machine governed by `on_busy` policies (wait, fail, force). If the requested model is not loaded, it attempts to load it via `ModelOrchestrator`, potentially unloading the existing model first. If the model is in use, `_wait_until_idle` handles the synchronization, either blocking until the model is free or forcing a cancellation if requested. History management involves atomic read/write operations to JSON files based on the active session path.

- **Side Effects:** The code interacts heavily with the filesystem via `load_history_from_json` and `save_history_to_json`. It communicates state changes to the external process monitoring system via `ProcessManager.set_state("activity", ...)`. It calls methods on the `ModelOrchestrator` to load/unload models, which inherently involves resource allocation (e.g., GPU memory).

- **Error Handling:** It raises `ModelNotFoundError` if the requested model ID cannot be found in configuration files. It raises `ModelLoadError` if the configuration is invalid or if the engine fails to load the model. It raises `ModelBusyError` if a swap is requested while the model is busy and the configured policy is `fail` or if the wait times out.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `threading`, `weakref`, `typing`, `os`, `json`, `datetime`.
- **Internal:** [ai.functions](/ai/functions.md), [ai.config](/ai/config.md), [ai.services.history_manager](/ai/services/history_manager.md), [ai.services.model_orchestrator](/ai/services/model_orchestrator.md), [ai.services.engine_manager](/ai/services/engine_manager.md), [ai.modules.server.exceptions](/ai/modules/server/exceptions.md), [ai.services.process_manager](/ai/services/process_manager.md).