## 1. Architectural Role
The `ModuleRegistry` class serves as the centralized plugin orchestrator for the JARVIS ecosystem. It manages the lifecycleincluding discovery, conditional instantiation, and graceful teardownof specialized functional modules. By utilizing a manifest-driven loading pattern, it decouples the core system from specific module implementations, providing a dictionary-style interface for other services to access active components like [modules/voice/vibe_module.md](modules/voice/vibe_module.md), [modules/memory/vector_memory_module.md](modules/memory/vector_memory_module.md), and [modules/knowledge_graph/__init__.md](modules/knowledge_graph/__init__.md).

## 2. Environment & Configuration
**Environment Lookups:**
- `VOICE_ENABLED` (via `config.get`)  Boolean flag to trigger [modules/voice/vibe_module.md](modules/voice/vibe_module.md) loading.
- `VECTOR_MEMORY_ENABLED` (via `config.get`)  Boolean flag to trigger [modules/memory/vector_memory_module.md](modules/memory/vector_memory_module.md) loading.
- `KNOWLEDGE_GRAPH_ENABLED` (via `config.get`)  Boolean flag to trigger [modules/knowledge_graph/__init__.md](modules/knowledge_graph/__init__.md) loading.
- `VOICE_FILE` (via `ProgramSetting.VOICE_FILE`)  Path to audio assets for the voice engine.
- `VECTOR_DB_PATH` (via `config.get`)  Filesystem path for the vector database.
- `VECTOR_RECENCY_WEIGHT` (via `config.get`)  Weighting factor for recency in vector retrieval.
- `VECTOR_IMPORTANCE_WEIGHT` (via `config.get`)  Weighting factor for importance in vector retrieval.
- `VECTOR_RELEVANCE_WEIGHT` (via `config.get`)  Weighting factor for relevance in vector retrieval.

**Hardcoded Constants:**
- `volume` (Default: `1.5`)  Audio output gain for `VibeVoiceModule`.
- `timeout` (Default: `2.0`)  Seconds to wait for module threads to join during unloading.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ModuleRegistry` | Class | Manages the lifecycle and access of all system modules. |
| `__getitem__` | Method | Provides dictionary-like access to active modules (e.g., `registry['voice']`). |
| `items` | Method | Returns a view of all currently active modules and their instances. |
| `load_all` | Method | Iterates through the internal manifest and boots enabled modules. |
| `unload_module` | Method | Executes shutdown/unload logic and cleans up resources for a specific module. |
| `unload_all` | Method | Performs a bulk shutdown of all active modules in the registry. |
| `shutdown` | Method | Alias for `unload_all` to ensure compatibility. |

## 4. Execution Logic & Flow
- **Initialization**: 
    1. Receives `ProgramConfig` instance.
    2. Initializes `_active_modules` dictionary.
    3. Maps module identifiers to internal loader functions via `_manifest`.
- **Data Path (Loading)**: 
    1. `load_all()` iterates over `_manifest`.
    2. Checks `config` for `{MODULE}_ENABLED` status.
    3. If `True`, calls specific `_load_{name}_logic` method.
    4. Logic method validates engine installation via [services/engine_manager.md](services/engine_manager.md).
    5. Logic method performs dynamic import of module class.
    6. Instance is stored in `_active_modules`.
- **Conditional Branching**:
    - **Engine Check**: If `EngineManager.is_engine_installed` returns `False`, loading for that module aborts with an error.
    - **Module Unloading**: Checks for `unload()` vs `shutdown()` methods to ensure compatibility with various module implementations.
    - **Thread Cleanup**: If a module has a `thread` attribute, it attempts a timed `join(2.0)`.

## 5. Resource Dependencies
- **Standard Libraries**: `typing`
- **Internal Modules**: 
    - [entities/model_enums.md](entities/model_enums.md)
    - [services/engine_manager.md](services/engine_manager.md)
    - [services/config_helper.md](services/config_helper.md)
    - [functions.md](functions.md)
    - [modules/voice/vibe_module.md](modules/voice/vibe_module.md)
    - [modules/memory/vector_memory_module.md](modules/memory/vector_memory_module.md)
    - [modules/knowledge_graph/__init__.md](modules/knowledge_graph/__init__.md)
- **External Packages**: None identified.