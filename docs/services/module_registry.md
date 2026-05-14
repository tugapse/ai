## 1. Architectural Role
Acts as a dynamic plugin manager responsible for the lifecycle orchestration, conditional instantiation, and dictionary-style access of JARVIS system modules.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ModuleRegistry` | Class | Manages the loading, storage, and unloading of system modules. |
| `__init__` | Method | Initializes the registry with a `ProgramConfig` and defines the module manifest. |
| `__getitem__` | Method | Provides dictionary-style access to active modules via string keys. |
| `items` | Method | Returns an iterator of the currently active modules and their instances. |
| `load_all` | Method | Iterates through the manifest and boots modules if enabled in configuration. |
| `_load_voice_logic` | Method | Validates `EngineType.VOICE_ENGINE` and instantiates `VibeVoiceModule`. |
| `_load_vector_memory_logic` | Method | Validates `EngineType.VECTOR_MEMORY` and instantiates `VectorMemoryModule` with weighted parameters. |
| `_load_knowledge_graph_logic` | Method | Instantiates `KnowledgeGraph` and attempts auto-wiring via `register_with_orchestrator`. |
| `unload_module` | Method | Executes `unload` or `shutdown` on a specific module and joins its thread if applicable. |
| `unload_all` | Method | Sequentially triggers the unloading process for all active modules. |
| `shutdown` | Method | Provides a compatibility alias for `unload_all`. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. Receives `ProgramConfig` instance.
    2. Initializes `_active_modules` as an empty dictionary.
    3. Populates `_manifest` with mapping of module keys to internal loader methods.
- **Data Path**: 
    1. **Input**: Configuration keys (e.g., `VOICE_ENABLED`, `VECTOR_DB_PATH`).
    2. **Processing**: `load_all` checks configuration $\rightarrow$ calls specific `_load_*_logic` $\rightarrow$ validates engine installation via `EngineManager` $\rightarrow$ instantiates module class.
    3. **Output**: Populated `_active_modules` dictionary containing live module instances.
- **Conditional Branching**:
    - **Module Activation**: Checks `bool(config.get(f"{mod_name.upper()}_ENABLED"))` to decide whether to execute loader.
    - **Engine Validation**: Checks `EngineManager.is_engine_installed()` before attempting module instantiation.
    - **Module Teardown**: Checks for existence of `unload` vs `shutdown` methods and checks if `instance.thread.is_alive()` before joining.
    - **KG Integration**: Attempts `kg.register_with_orchestrator()`; if missing, attempts module-level `register_with_orchestrator()`.

## 4. Resource Dependencies
- **Standard Libraries**: `typing`
- **Internal Modules**: `entities.model_enums`, `services.engine_manager`, `services.config_helper`, `functions` (as `func`), `modules.voice.vibe_module`, `modules.memory.vector_memory_module`, `modules.knowledge_graph`
- **External Packages**: None explicitly imported (relies on internal abstractions)

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `volume=1.5` (Voice module)
    - `timeout=2.0` (Thread join timeout)
- **Environment Lookups**:
    - `{MOD_NAME}_ENABLED` (e.g., `VOICE_ENABLED`, `VECTOR_MEMORY_ENABLED`, `KNOWLEDGE_GRAPH_ENABLED`)
    - `ProgramSetting.VOICE_FILE`
    - `VECTOR_DB_PATH`
    - `VECTOR_RECENCY_WEIGHT`
    - `VECTOR_IMPORTANCE_WEIGHT`
    - `VECTOR_RELEVANCE_WEIGHT`