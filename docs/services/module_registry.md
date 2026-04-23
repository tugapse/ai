## 1. Architectural Role
The `ModuleRegistry` acts as a dynamic plugin manager responsible for the conditional instantiation, lifecycle management, and centralized access of system modules based on the `ProgramConfig`.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ModuleRegistry` | Class | Orchestrates the loading, storage, and unloading of system modules. |
| `__init__` | Method | Initializes the registry with a config object and defines the module loader manifest. |
| `__getitem__` | Method | Provides dictionary-style access to active modules via string keys. |
| `load_all` | Method | Iterates through the manifest and instantiates modules enabled in the configuration. |
| `_load_server_logic` | Method | Configures and instantiates `JarvisServerModule`. |
| `_load_client_logic` | Method | Configures and instantiates `RemoteConnectorModule`. |
| `_load_voice_logic` | Method | Validates voice engine installation and instantiates `VibeVoiceModule`. |
| `_load_vector_memory_logic` | Method | Validates memory engine installation and instantiates `VectorMemoryModule`. |
| `shutdown` | Method | Iterates through active modules to trigger their unloading process. |

## 3. Execution Logic & Flow
- **Initialization**: 
    1. Receives `ProgramConfig` instance.
    2. Initializes `_active_modules` as an empty dictionary.
    3. Maps module keys (`voice`, `vector_memory`, `server_hub`, `client_link`) to their respective internal loader methods in `_manifest`.
- **Data Path**: `ProgramConfig` $\rightarrow$ `load_all()` $\rightarrow$ `_load_[module]_logic()` $\rightarrow$ `_active_modules` $\rightarrow$ `__getitem__` (External Access).
- **Conditional Branching**:
    1. **Enablement Check**: In `load_all`, the registry checks if `{MOD_NAME}_ENABLED` is `True` in the config before calling the loader.
    2. **Dependency Validation**: `_load_voice_logic` and `_load_vector_memory_logic` check `EngineManager.is_engine_installed` before proceeding.
    3. **Configuration Validation**: `_load_client_logic` verifies the existence of `REMOTE_BRAIN_URL`; if missing, it aborts loading.
    4. **Import Safety**: All loader methods wrap imports in `try-except ImportError` blocks to prevent system crash on missing module files.

## 4. Resource Dependencies
- **Standard Libraries**: `typing` (`Dict`, `Any`, `Optional`)
- **Internal Modules**: 
    - `entities.model_enums.EngineType`
    - `services.model_manager.EngineManager`
    - `config.ProgramConfig`, `config.ProgramSetting`
    - `functions` (aliased as `func`)
    - `modules.server.server_module.JarvisServerModule`
    - `modules.client.remote_module.RemoteConnectorModule`
    - `modules.voice.vibe_module.VibeVoiceModule`
    - `modules.memory.vector_memory_module.VectorMemoryModule`

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - Default Server Host: `"0.0.0.0"`
    - Default Server Port: `8000`
    - Default Model Config Name: `"default"`
- **Environment Lookups**:
    - `VOICE_ENABLED`, `VECTOR_MEMORY_ENABLED`, `SERVER_HUB_ENABLED`, `CLIENT_LINK_ENABLED`
    - `SERVER_HOST`, `SERVER_PORT`
    - `REMOTE_BRAIN_URL`, `MODEL_CONFIG_NAME`
    - `VECTOR_DB_PATH`
    - `VECTOR_RECENCY_WEIGHT`, `VECTOR_IMPORTANCE_WEIGHT`, `VECTOR_RELEVANCE_WEIGHT`