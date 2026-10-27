## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | BrainHub |
| Source file | brain_hub.py |

The **BrainHub** serves as the central nervous system for the server module, acting as the high-level controller that bridges the gap between session management, conversational history, and the active Large Language Model (LLM). It is responsible for the lifecycle of the "brain"managing when models are loaded into VRAM, when they are swapped to prevent memory overflow, and how the conversational context (history) is persisted to disk.

By orchestrating the interaction between [ModelOrchestrator](/docs/ai/services/model_orchestrator.md) and the session state, it ensures that the server maintains a coherent state across different user sessions. It acts as a gatekeeper for model resources, ensuring that only the necessary model is "HOT" (active in memory) while providing a unified interface for the API to interact with the underlying LLM capabilities and token statistics.

**Functional Mission**
The primary mission of **BrainHub** is to manage the active execution state of the AI, specifically handling the hot-swapping of LLM instances and the synchronization of session-based JSON memory files.

**System Context & Integration**
**BrainHub** sits between the API routing layer and the core LLM services. It consumes configurations from [ProgramConfig](/docs/ai/config.md) and utilizes [ModelOrchestrator](/docs/ai/services/model_orchestrator.md) to perform the heavy lifting of model loading. When a session is routed, it updates its internal history state, which is then used to feed context into the LLM. It also provides telemetry via `get_stats`, allowing downstream monitoring components to track token usage and context window saturation.

- **INTERNAL REFERENCES**: 
    - [ModelOrchestrator](/docs/ai/services/model_orchestrator.md)
    - [ProgramConfig](/docs/ai/config.md)
    - [ProgramSetting](/docs/ai/config.md)
    - [HistoryManager](/docs/ai/services/history_manager.md)
    - [ai.functions](/docs/ai/functions.md)

## 2. Environment & Configuration
**Environment Lookups:**
- `ProgramSetting.PATHS_MODEL_CONFIGS` (via `list_available_models`)  Retrieves the directory path containing available model JSON configurations.

**Hardcoded Constants:**
- No hardcoded constants identified.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `BrainHub` | Class | Main controller for model lifecycle and session memory. |
| `new_history` | Func | Generates a standardized dictionary structure for new chat sessions. |
| `route_memory` | Func | Performs a "hot-swap" of the active history file and resets session metadata. |
| `add_history_message` | Func | Appends a role/content pair to the current history and triggers an immediate disk save. |
| `load_history_from_json` | Func | Deserializes a JSON file into the active history, including validation logic. |
| `save_history_to_json` | Func | Serializes the current history dictionary to a physical JSON file. |
| `get_timestamp` | Func | Returns an ISO-formatted string for temporal tracking. |
| `get_brain` | Func | The primary entry point for model access; handles model swapping and system prompt updates. |
| `unload_brain` | Func | Explicitly triggers the unloading of the current LLM to free VRAM. |
| `list_available_models` | Func | Returns a list of model identifiers available in the config directory. |
| `get_stats` | Func | Returns a dictionary containing token usage, window size, and context saturation. |

## 4. Execution Logic & Flow
- **Initialization**: 
    - Receives `ProgramConfig`.
    - Instantiates `ModelOrchestrator`.
    - Initializes a default, empty history structure via `new_history`.
- **Data Path (History Management)**:
    - **Input**: `role` (str), `content` (str).
    - **Processing**: Appends message to `self.history["messages"]` $\rightarrow$ Updates `last_updated` via `get_timestamp()` $\rightarrow$ Calls `save_history_to_json`.
    - **Output**: Persistent JSON file on disk.
- **Data Path (Model Acquisition)**:
    - **Input**: `model_id`, `system_prompt`, `model_config_data`.
    - **Decision Point**: Is `current_model_id` different from requested `model_id`?
        - **Yes**: Call `unload_brain()` to clear VRAM.
    - **Decision Point**: Is `orchestrator.llm` already loaded?
        - **Yes**: Check if `system_prompt` matches. If not, update it. Return `llm`.
        - **No**: Call `orchestrator.load(...)` $\rightarrow$ Set `current_model_id` $\rightarrow$ Return `llm`.
- **Conditional Branching (JSON Loading)**:
    - **Check**: Does file exist?
        - **No**: Log warning, reset history to empty.
        - **Yes**: Attempt `json.load`.
            - **Success**: Validate schema (is dict, has 'messages' list).
                - **Valid**: Overwrite `self.history`.
                - **Invalid**: Log warning, clear messages/timestamp.
            - **JSONDecodeError**: Log error, clear messages/timestamp.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `json`, `typing.Optional`, `datetime.datetime`
- **Internal Modules**: 
    - [ai.functions](/docs/ai/functions.md)
    - [ProgramConfig](/docs/ai/config.md)
    - [ProgramSetting](/docs/ai/config.md)
    - [HistoryManager](/docs/ai/services/history_manager.md)
    - [ModelOrchestrator](/docs/ai/services/model_orchestrator.md)
- **External Packages**: None identified.