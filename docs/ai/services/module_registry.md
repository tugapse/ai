## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | ModuleRegistry |
| Source file | module_registry.py |

The **ModuleRegistry** serves as the centralized plugin management system for the JARVIS architecture. It acts as a lifecycle controller, responsible for the dynamic discovery, instantiation, and teardown of specialized functional modules. By decoupling the core system from specific module implementations, it provides a unified interface for managing disparate capabilities like voice synthesis, long-term memory, and structured knowledge representation.

**Functional Mission**
The primary responsibility of the **ModuleRegistry** is to manage the lifecycle of all active system modules. It solves the problem of heterogeneous module initialization by providing a standardized manifest-driven loading mechanism, ensuring that modules are only instantiated if explicitly enabled in the system configuration and that they are gracefully decommissioned to prevent resource leaks.

**System Context & Integration**
This component sits between the global configuration layer and the functional module layer. During the system boot sequence, it consumes settings from [ProgramConfig](/docs/ai/services/config_helper.md) to determine which modules to activate. Once loaded, it populates an internal registry that allows other services to access modules via dictionary-style lookup. It integrates deeply with [EngineManager](/docs/ai/services/engine_manager.md) to verify hardware/software dependencies before attempting to boot modules like [VibeVoiceModule](/docs/ai/modules/voice/vibe_module.md) or [VectorMemoryModule](/docs/ai/modules/vector_memory/vector_memory_module.md).

- **INTERNAL REFERENCES**: 
    - [ProgramConfig](/docs/ai/services/config_helper.md)
    - [EngineManager](/docs/ai/services/engine_manager.md)
    - [BaseModule](/docs/ai/modules/base_module.md)
    - [EngineType](/docs/ai/entities/model_enums.md)
    - [ProgramSetting](/docs/ai/services/config_helper.md)
    - [KnowledgeGraph](/docs/ai/modules/knowledge_graph/manager.md)

## 2. Environment & Configuration
**Environment Lookups:**
- `VOICE_ENABLED` (via `load_all`)  Boolean flag to trigger [VibeVoiceModule](/docs/ai/modules/voice/vibe_module.md) loading.
- `VECTOR_MEMORY_ENABLED` (via `load_all`)  Boolean flag to trigger [VectorMemoryModule](/docs/ai/modules/vector_memory/vector_memory_module.md) loading.
- `KNOWLEDGE_GRAPH_ENABLED` (via `load_all`)  Boolean flag to trigger [KnowledgeGraph](/docs/ai/modules/knowledge_graph/manager.md) loading.

**Hardcoded Constants:**
- `volume` (Default: `1.5`)  Fixed gain applied to the voice module during initialization.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `__init__` | Method | Initializes the registry with a configuration object and defines the module manifest. |
| `__getitem__` | Method | Provides dictionary-style access to active modules using a string key. |
| `items` | Method | Returns an iterator over the currently active modules and their instances. |
| `load_all` | Method | Iterates through the manifest and boots all modules marked as enabled in the config. |
| `_load_voice_logic` | Method | Private loader for the voice module; checks engine availability and preloads assets. |
| `_load_vector_memory_logic` | Method | Private loader for vector memory; configures weights and database paths. |
| `_load_knowledge_graph_logic` | Method | Private loader for the KG; handles orchestration registration and preloading. |
| `unload_module` | Method | Performs a graceful shutdown of a specific module (calls `unload`, `shutdown`, or joins threads). |
| `unload_all` | Method | Iterates through all active modules to trigger a global shutdown. |
| `shutdown` | Method | Alias for `unload_all` to support legacy shutdown calls. |

## 4. Execution Logic & Flow
- **Initialization**: 
    1. Receives `ProgramConfig`.
    2. Initializes `_active_modules` as an empty dictionary.
    3. Maps module keys (`voice`, `vector_memory`, `knowledge_graph`) to internal loader methods in `_manifest`.
- **Data Path (Loading)**: 
    1. `load_all` iterates through `_manifest`.
    2. Checks `config` for `{MODULE}_ENABLED`.
    3. If `True`, calls the corresponding `_load_{module}_logic` method.
    4. Loader method verifies engine status via `EngineManager`.
    5. Loader method instantiates the module (e.g., `VectorMemoryModule`) with parameters from `ProgramSetting`.
    6. Instance is stored in `_active_modules`.
- **Conditional Branching**:
    - **Engine Check**: If `EngineManager.is_engine_installed` returns `False`, the loader logs an error and returns `None`.
    - **Import Error**: If a module import fails (e.g., `VectorMemoryModule`), the error is caught, logged, and the registry continues.
    - **Unload Strategy**: `unload_module` checks for `unload()` first, then `shutdown()`, then attempts to `join()` the module's thread if it exists.

## 5. Resource Dependencies
- **Standard Libraries**: `typing`
- **Internal Modules**: 
    - [EngineType](/docs/ai/entities/model_enums.md)
    - [BaseModule](/docs/ai/modules/base_module.md)
    - [EngineManager](/docs/ai/services/engine_manager.md)
    - [ProgramConfig](/docs/ai/services/config_helper.md)
    - [ProgramSetting](/docs/ai/services/config_helper.md)
    - [func](/docs/ai/functions.md)
    - [VibeVoiceModule](/docs/ai/modules/voice/vibe_module.md)
    - [VectorMemoryModule](/docs/ai/modules/vector_memory/vector_memory_module.md)
    - [KnowledgeGraph](/docs/ai/modules/knowledge_graph/manager.md)
- **External Packages**: None identified.