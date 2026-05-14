## 1. Architectural Role

**Functional Mission**
The **ModuleRegistry** serves as the centralized plugin management system for the JARVIS architecture. Its primary responsibility is to manage the lifecycle of various functional modulesspecifically voice, vector memory, and knowledge graph componentsby dynamically loading, accessing, and unloading them based on the system's configuration state.

**System Context & Integration**
This component acts as a gatekeeper between the core system configuration and the specialized functional modules. It interfaces with [ProgramConfig](/docs/services/config_helper.md) to determine which modules should be instantiated and utilizes [EngineManager](/docs/services/engine_manager.md) to verify the presence of required underlying engines before attempting to boot a module. Once loaded, it provides a dictionary-style interface for other system components to access active module instances, facilitating seamless integration between the orchestrator and specialized services like [VibeVoiceModule](/docs/modules/voice/vibe_module.md), [VectorMemoryModule](/docs/modules/memory/vector_memory_module.md), and [KnowledgeGraph](/docs/modules/knowledge_graph/__init__.md).

## 2. Environment & Configuration

**Environment Lookups:**
- `VOICE_ENABLED` (via `load_all`)  Determines if the voice module should be initialized.
- `VECTOR_MEMORY_ENABLED` (via `load_all`)  Determines if the vector memory module should be initialized.
- `KNOWLEDGE_GRAPH_ENABLED` (via `load_all`)  Determines if the knowledge graph module should be initialized.
- `VOICE_FILE` (via `_load_voice_logic`)  Path to the voice asset file.
- `VECTOR_DB_PATH` (via `_load_vector_memory_logic`)  Filesystem path for the vector database.
- `VECTOR_RECENCY_WEIGHT` (via `_load_vector_memory_logic`)  Weighting factor for recency in memory retrieval.
- `VECTOR_IMPORTANCE_WEIGHT` (via `_load_vector_memory_logic`)  Weighting factor for importance in memory retrieval.
- `VECTOR_RELEVANCE_WEIGHT` (via `_load_vector_memory_logic`)  Weighting factor for relevance in memory retrieval.

**Hardcoded Constants:**
- `volume` (Default: `1.5`)  Audio output volume for the voice module.
- `timeout` (Default: `2.0`)  Seconds to wait when joining module threads during unloading.

## 3. Interface & API Surface

| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ModuleRegistry` | Class | Orchestrates the lifecycle (load/unload/shutdown) of system modules. |
| `__getitem__` | Method | Provides dictionary-style access to active modules via string keys. |
| `items` | Method | Returns an iterator over the active modules and their instances. |
| `load_all` | Method | Iterates through the manifest and boots enabled modules. |
| `_load_voice_logic` | Method | Internal loader for the voice module; validates engine presence. |
| `_load_vector_memory_logic` | Method | Internal loader for the vector memory module; configures weights. |
| `_load_knowledge_graph_logic` | Method | Internal loader for the knowledge graph; handles auto-wiring. |
| `unload_module` | Method | Gracefully shuts down a specific module and cleans up resources. |
| `unload_all` | Method | Triggers a sequential shutdown of all currently active modules. |
| `shutdown` | Method | Alias for `unload_all` to provide API compatibility. |

## 4. Execution Logic & Flow

- **Initialization**: The registry is instantiated with a `ProgramConfig` object. It initializes an empty `_active_modules` dictionary and defines a `_manifest` mapping module names to their respective internal loader functions.
- **Data Path**: 
    1. `load_all` iterates through `_manifest`.
    2. Configuration is queried for `[MODULE]_ENABLED`.
    3. If `True`, the corresponding `_load_[module]_logic` function is invoked.
    4. The resulting instance is stored in `_active_modules`.
    5. Downstream components access these instances via `__getitem__`.
- **Conditional Branching**:
    - **Engine Check**: Before loading voice or vector memory, `EngineManager.is_engine_installed` is checked; if it fails, the module load is aborted with an error log.
    - **Import Error Handling**: `_load_vector_memory_logic` and `_load_knowledge_graph_logic` use `try-except` blocks to catch `ImportError` or general exceptions, preventing a single module failure from crashing the entire registry.
    - **Unload Logic**: `unload_module` checks for specific cleanup methods (`unload` vs `shutdown`) and attempts to join threads if a `thread` attribute is present.

## 5. Resource Dependencies

- **Standard Libraries**: `typing`
- **Internal Modules**: 
    - [EngineType](/docs/entities/model_enums.md)
    - [EngineManager](/docs/services/engine_manager.md)
    - [ProgramConfig](/docs/services/config_helper.md)
    - [ProgramSetting](/docs/services/config_helper.md)
    - [functions](/docs/functions.md)
    - [VibeVoiceModule](/docs/modules/voice/vibe_module.md)
    - [VectorMemoryModule](/docs/modules/memory/vector_memory_module.md)
    - [KnowledgeGraph](/docs/modules/knowledge_graph/__init__.md)
- **External Packages**: None identified.