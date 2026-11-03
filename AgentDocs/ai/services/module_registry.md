## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **ModuleRegistry** | [src/ai/services/module_registry.py](/AgentDocs/ai/services/module_registry.md) |

The `ModuleRegistry` acts as the central Plugin Manager for the JARVIS ecosystem. Its primary responsibility is to manage the lifecycle of various functional modulessuch as voice processing, vector memory, and knowledge graphsby handling their dynamic loading, instantiation, and safe unloading based on the system configuration.

Within the broader application architecture, this component serves as a service-layer controller that bridges the gap between global configuration and active functional modules. It ensures that only requested modules are initialized, preventing unnecessary resource consumption while providing a standardized dictionary-style interface for other services to access active module instances.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `__init__(config: ProgramConfig)` | Class Method | Initializes the registry with a [ProgramConfig](/AgentDocs/ai/services/config_helper.md) object. |
| `__getitem__(key: str)` | Magic Method | Enables dictionary-style access (e.g., `registry['voice']`) to retrieve an active [BaseModule](/AgentDocs/ai/modules/base_module.md). |
| `items()` | Method | Returns a view of all currently active module names and their corresponding [BaseModule](/AgentDocs/ai/modules/base_module.md) instances. |
| `load_all()` | Method | Iterates through the internal manifest and instantiates all modules marked as enabled in the configuration. |
| `unload_module(name: str)` | Method | Safely shuts down and removes a specific module by name, attempting to call `unload()` or `shutdown()` methods. |
| `unload_all()` | Method | Triggers a global shutdown sequence for all currently active modules. |
| `shutdown()` | Method | Alias for `unload_all()`; used for compatibility during system teardown. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The registry utilizes an internal `_manifest` mapping string identifiers to specific private loader functions (`_load_voice_logic`, `_load_vector_memory_logic`, and `_load_knowledge_graph_logic`). During `load_all()`, the registry performs a lookup in the [ProgramConfig](/AgentDocs/ai/services/config_helper.md) using a convention of `{MODULE_NAME}_ENABLED`. If true, the corresponding loader is executed.
- **Side Effects:** 
    - **Filesystem/Database:** The `_load_vector_memory_logic` may access or define paths for vector databases.
    - **Resource Management:** Loading modules may trigger hardware initialization (e.g., Voice Engine) or thread creation.
    - **Logging:** Extensive use of [func](/AgentDocs/ai/functions.md) for logging module boot and shutdown sequences.
- **Error Handling:** The registry implements "graceful failure" patterns. If a module fails to import or its engine is not installed (checked via [EngineManager](/AgentDocs/ai/services/engine_manager.md)), the registry logs an error and continues with the next module rather than crashing the entire boot sequence. It also includes specific try-except blocks for `KnowledgeGraph` integration hooks.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- `ProgramConfig`  Used to determine which modules are enabled and to retrieve specific module settings like `VOICE_FILE` or `VECTOR_DB_PATH`.

**Module Dependencies:**
- **Standard/External:** `typing`
- **Internal:**
    - [EngineType](/AgentDocs/ai/entities/model_enums.md)
    - [BaseModule](/AgentDocs/ai/modules/base_module.md)
    - [EngineManager](/AgentDocs/ai/services/engine_manager.md)
    - [ProgramConfig](/AgentDocs/ai/services/config_helper.md)
    - [ProgramSetting](/AgentDocs/ai/services/config_helper.md)
    - [func](/AgentDocs/ai/functions.md)
    - [VibeVoiceModule](/AgentDocs/ai/modules/voice/vibe_module.md)
    - [VectorMemoryModule](/AgentDocs/ai/modules/vector_memory/vector_memory_module.md)
    - [KnowledgeGraph](/AgentDocs/ai/modules/knowledge_graph/manager.md) (via dynamic import)