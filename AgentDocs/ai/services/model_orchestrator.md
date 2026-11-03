## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **ModelOrchestrator** | [src/ai/services/model_orchestrator.py](/AgentDocs/ai/services/model_orchestrator.md) |

The `ModelOrchestrator` is responsible for the lifecycle management of Large Language Models (LLMs) within the application. It handles the resolution of model configuration files, manages the transition between different active models, and ensures that the appropriate `BaseModel` instance is initialized with the correct system prompts and tool registries.

As a service-layer component, it acts as a high-level controller that abstracts the complexities of model loading from the rest of the system. It coordinates between the `DirectoryManager` for file resolution, the `EngineManager` for instantiation, and the `ToolRegistry` for capability injection, providing a unified interface for the application to interact with various LLM backends.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `ModelOrchestrator(config: ProgramConfig)` | Class | Initializes the orchestrator with the global `ProgramConfig`. |
| `load(model_config_name: str, system_prompt: str, tool_registry: Optional[ToolRegistry] = None, model_config_data: Optional[dict] = None) -> BaseModel` | Method | Resolves configuration, shuts down any existing model, and loads a new `BaseModel` instance. |
| `get_params() -> Dict[str, Any]` | Method | Returns the current dictionary of model parameters (e.g., temperature, top_p). |
| `get_chat_name() -> str` | Method | Returns the human-readable name associated with the active model's chat context. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The `load` method implements a hierarchical configuration resolution strategy. It first checks if `model_config_data` is provided; if not, it searches for a `.json` configuration file in the system model directory, falling back to the user model directory if a user-specific version exists. It ensures that if a new model is requested, the current `llm` instance undergoes a `request_shutdown()` to prevent resource leaks or conflicting processes.
- **Side Effects:** 
    - **Filesystem:** Reads model configuration `.json` files from system and user directories via `DirectoryManager`.
    - **Process Management:** Calls `sys.exit(1)` on critical failures during model loading or configuration parsing.
    - **State Mutation:** Mutates the internal `self.llm`, `self.model_params`, and `self.active_model_name` attributes.
- **Error Handling:** The component uses a "fail-fast" approach for critical errors. If a configuration cannot be loaded or a model fails to initialize, it logs a `CRITICAL` error via `ai.functions` and terminates the process.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- No direct environment variables are accessed within this component; it relies on the passed `ProgramConfig`.

**Module Dependencies:**
- **Standard/External:** `os`, `sys`, `typing`.
- **Internal:**
    - [ai.functions](/AgentDocs/ai/functions.md)
    - [ai.services.directory_manager](/AgentDocs/ai/services/directory_manager.md)
    - [ai.services.engine_manager](/AgentDocs/ai/services/engine_manager.md)
    - [ai.core.llms.base_llm](/AgentDocs/ai/core/llms/base_llm.md)
    - [ai.services.config_helper](/AgentDocs/ai/services/config_helper.md)
    - [ai.tools.tool_registry](/AgentDocs/ai/tools/tool_registry.md)