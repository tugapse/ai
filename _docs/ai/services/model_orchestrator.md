## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| ModelOrchestrator | /ai/services/model_orchestrator.md |

This component is the central manager responsible for the lifecycle of language models within the application. Its primary responsibility is to locate the correct model configuration (prioritizing user settings over system defaults), load the specified LLM instance using the `EngineManager`, and maintain the state of the currently active model, including its parameters and chat identity.

As a core service, `ModelOrchestrator` acts as a high-level controller within the application architecture. It abstracts the complexities of model discovery and instantiation, allowing other parts of the system to request a functional `BaseModel` without needing to know the underlying loading mechanisms or configuration file locations. It heavily relies on [DirectoryManager](/ai/services/directory_manager.md) for path resolution and [EngineManager](/ai/services/engine_manager.md) for the actual model instantiation.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| ModelOrchestrator | Class | Manages the loading, configuration, and lifecycle of various language models. |
| ModelOrchestrator.config_folders | Static Method | Returns a list of directories containing model configurations in priority order. |
| ModelOrchestrator.find_config_file | Static Method | Returns the absolute path to a model configuration file based on its name, respecting directory precedence. |
| ModelOrchestrator.list_config_files | Static Method | Scans all configured directories and returns a dictionary mapping model keys to their absolute configuration file paths. |
| ModelOrchestrator.load | Method | Loads a specific language model instance, handling configuration resolution, shutdown of previous models, and GPU memory fallbacks. |
| ModelOrchestrator.get_params | Method | Retrieves the current set of parameters associated with the active model. |
| ModelOrchestrator.get_chat_name | Method | Retrieves the designated chat name for the currently active model. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The `load` method orchestrates a multi-step process: first, it resolves the configuration file path using `find_config_file` or loads data directly; second, it ensures any previously active LLM is properly shut down; third, it attempts to instantiate the model via `EngineManager.load_model_instance`; and finally, it handles potential `GpuMemoryError` by invoking the `GpuAdvisor` for partial or alternative loading strategies.
- **Side Effects:** Reads from the filesystem (via `DirectoryManager` and `os.walk` in `list_config_files`), potentially exits the process (`sys.exit(1)`) upon critical failure, and calls shutdown methods on existing LLM instances.
- **Error Handling:** Catches `GpuMemoryError` to trigger a fallback mechanism involving `GpuAdvisor` (either partial loading or resolving alternatives). It also catches general exceptions during loading, either exiting or logging via `func.error`.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `os`, `sys`, `typing`
- **Internal:** [ai.functions](/ai/functions.md), [ai.services.directory_manager](/ai/services/directory_manager.md), [ai.services.engine_manager](/ai/services/engine_manager.md), [ai.core.llms.load_errors](/ai/core/llms/load_errors.md), [ai.core.llms.base_llm](/ai/core/llms/base_llm.md), [ai.services.config_helper](/ai/services/config_helper.md), [ai.tools.tool_registry](/ai/tools/tool_registry.md), [ai.services.gpu_advisor](/ai/services/gpu_advisor.md)