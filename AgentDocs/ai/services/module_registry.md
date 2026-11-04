## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **ModuleRegistry** | [src/ai/services/module_registry.py](/src/ai/services/module_registry.py) |

The `ModuleRegistry` acts as the central plugin manager for the JARVIS ecosystem. It is responsible for the lifecycle management of various functional modules, including voice processing, vector memory, and knowledge graph integration. By providing a unified interface for loading, accessing, and unloading these modules, it ensures that the system can dynamically scale its capabilities based on the provided configuration.

In the broader system architecture, this component serves as a service-level controller that bridges the gap between global configuration and specialized functional modules. It utilizes the `ProgramConfig` to determine which modules should be instantiated and relies on the `EngineManager` to verify that necessary underlying engine dependencies are installed before attempting to boot a module.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `ModuleRegistry(config: ProgramConfig)` | Class | Initializes the registry with a global configuration object. |
| `__getitem__(key: str) -> Optional[BaseModule]` | Method | Enables dictionary-style access (e.g., `registry['voice']`) to retrieve active modules. |
| `items()` | Method | Returns a view of all currently active module names and their corresponding `BaseModule` instances. |
| `load_all()` | Method | Iterates through the internal manifest and instantiates all modules marked as enabled in the configuration. |
| `unload_module(name: str)` | Method | Safely shuts down a specific module by calling its `unload` or `shutdown` methods and joining its execution thread. |
| `unload_all()` | Method | Triggers a global shutdown sequence for all currently active modules. |
| `shutdown()` | Method | Alias for `unload_all()`; initiates the global shutdown sequence. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The registry maintains an internal `_manifest` mapping module identifiers (e.g., `"voice"`, `"vector_memory"`) to private loader functions. During `load_all()`, it constructs configuration lookup keys (e.g., `VOICE_ENABLED`) to decide whether to execute the associated loader. Loaders perform dependency checks via `EngineManager` and handle local imports of specific module classes to avoid circular dependencies or heavy startup overhead.
- **Side Effects:** 
    - **Filesystem/Database:** Loading the `vector_memory` module interacts with the filesystem to locate or initialize database paths.
    - **Threading:** The `unload_module` method attempts to join module threads with a 2.0-second timeout to ensure clean exits.
    - **Logging:** Extensive use of `func.log`, `func.debug`, and `func.error` for system telemetry.
- **Error Handling:** The registry uses broad `try-except` blocks during module loading and unloading to prevent a single failing module from crashing the entire bootstrap process. If an import fails or an engine is missing, the registry logs an error and continues with the remaining modules.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- `[ProgramConfig](/ai/services/config_helper.md)`  Used to check module enablement flags (e.g., `VOICE_ENABLED`) and retrieve module-specific settings like `VOICE_FILE` or `VECTOR_DB_PATH`.

**Module Dependencies:**
- **Standard/External:** `typing` (Dict, Any, Optional).
- **Internal:**
    - [EngineType](/ai/entities/model_enums.md)
    - [BaseModule](/ai/modules/base_module.md)
    - [EngineManager](/ai/services/engine_manager.md)
    - [ProgramConfig](/ai/services/config_helper.md)
    - [ProgramSetting](/ai/services/config_helper.md)
    - [ai.functions](/ai/functions.md)
    - [VibeVoiceModule](/ai/modules/voice/vibe_module.md)
    - [VectorMemoryModule](/ai/modules/vector_memory/vector_memory_module.md)
    - [KnowledgeGraph](/ai/modules/knowledge_graph/manager.md) (via dynamic import)