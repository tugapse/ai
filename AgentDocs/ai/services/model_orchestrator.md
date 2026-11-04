## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **ModelOrchestrator** | [src/ai/services/model_orchestrator.py](/src/ai/services/model_orchestrator.py) |

The `ModelOrchestrator` is responsible for the lifecycle management of Large Language Models (LLMs) within the application. It handles the resolution of model configurations, manages the transition between different active models, and ensures that model parameters and identities are correctly tracked and initialized.

As a service-layer component, it acts as a high-level controller that abstracts the complexities of model loading. It coordinates between the [DirectoryManager](/AgentDocs/ai/services/directory_manager.md) for locating configuration files, the [EngineManager](/AgentDocs/ai/services/engine_manager.md) for instantiating specific model engines, and the [ToolRegistry](/AgentDocs/ai/tools/tool_registry.md) for attaching capabilities to the loaded model.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `__init__(config: ProgramConfig)` | Class Constructor | Initializes the orchestrator with the global [ProgramConfig](/AgentDocs/ai/services/config_helper.md). |
| `load(model_config_name: str, system_prompt: str, tool_registry: Optional[ToolRegistry] = None, model_config_data: Optional[dict] = None) -> BaseModel` | Method | Resolves and loads a specific LLM instance. It handles file path resolution (system vs. user), shuts down existing models if a new one is requested, and returns an initialized [BaseModel](/AgentDocs/ai/core/llms/base_llm.md). |
| `get_params() -> Dict[str, Any]` | Method | Returns a dictionary of the current model's configuration parameters. |
| `get_chat_name() -> str` | Method | Returns the string identifier for the currently active model's chat context. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The `load` method implements a hierarchical configuration lookup. It first checks for provided `model_config_data`. If absent, it attempts to locate a `.json` configuration file in the user's model directory, falling back to the system model directory. It ensures that only one model is active at a time by calling `request_shutdown()` on the existing `llm` instance if the requested configuration differs from the `active_model_name`.
- **Side Effects:** 
    - **Filesystem:** Reads model configuration JSON files from disk via [DirectoryManager](/AgentDocs/ai/services/directory_manager.md).
    - **State Mutation:** Updates `self.llm`, `self.model_params`, `self.model_chat_name`, and `self.active_model_name` upon successful loading.
    - **Process Control:** Triggers model shutdown sequences via the loaded LLM instance.
- **Error Handling:** The component uses a "fail-fast" approach for critical errors. If a configuration file cannot be loaded or the `EngineManager` fails to produce a valid model instance, the orchestrator logs a `CRITICAL` error via [func.error](/AgentDocs/ai/functions.md) and terminates the process using `sys.exit(1)`.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No direct environment variables are accessed by this component; it relies on the passed `ProgramConfig` object.

**Module Dependencies:**
- **Standard/External:** `os`, `sys`, `typing`.
- **Internal:**
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ai.services.directory_manager](/AgentDocs/ai/services/directory_manager.md)
    - [ai.services.engine_manager](/AgentDocs/ai/services/engine_manager.md)
    - [ai.core.llms.base_llm](/AgentDocs/ai/core/llms/base_llm.md)
    - [ai.services.config_helper](/AgentDocs/ai/services/config_helper.md)
    - [ai.tools.tool_registry](/AgentDocs/ai/tools/tool_registry.md)