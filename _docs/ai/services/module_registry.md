## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| ModuleRegistry | /ai/services/module_registry.md |

This component serves as the central Plugin Manager for the entire JARVIS system, responsible for the discovery, loading, activation, and safe unloading of all functional modules. Its primary responsibility is to maintain a registry of active modules, allowing the rest of the application to access specialized capabilities (like voice processing, vector memory, or knowledge graph operations) through a unified interface.

Architecturally, `ModuleRegistry` functions as a core service layer, sitting above the application logic and interfacing with configuration systems like [ProgramConfig](/ai/services/config_helper.md). It orchestrates the initialization process by consulting a predefined manifest, ensuring that only modules explicitly enabled by the user configuration are brought online, thereby controlling the application's runtime behavior.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| `ModuleRegistry.__getitem__` | Method | Allows retrieval of an active module instance using its string key (e.g., `registry['voice']`). Returns the `BaseModule` or `None`. |
| `ModuleRegistry.items` | Method | Returns an iterable view of all currently active modules as (name, module) pairs. |
| `ModuleRegistry.load_all` | Method | Iterates through the internal manifest, checks configuration flags, and instantiates and activates all enabled modules. |
| `ModuleRegistry.tool_functions` | Method | Gathers and aggregates all callable tools exposed by active modules that implement the `ToolModule` interface, returning a dictionary of `{tool_name: callable}`. |
| `ModuleRegistry.unload_module` | Method | Safely deactivates and removes a single module by name, executing its defined cleanup routines. |
| `ModuleRegistry.unload_all` | Method | Executes a controlled shutdown sequence, iterating through and unloading every module currently active in the registry. |
| `ModuleRegistry.shutdown` | Method | Alias for `unload_all`, providing backward compatibility for global shutdown calls. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The registry uses a manifest dictionary (`self._manifest`) to map module names to their loading functions. The `load_all` method implements a configuration-driven loading strategy, checking for `*_ENABLED` flags in the global configuration. Modules are loaded dynamically, often involving external imports (like `ai.modules.tools_filesystem`). Unloading is managed by calling specific lifecycle methods (`unload` or `shutdown`) on the instance before removal.

- **Side Effects:** Reads from the global configuration (`ProgramConfig`). Interacts heavily with the filesystem when loading tool modules (e.g., `ai.modules.tools_filesystem`) and when initializing modules like `VectorMemoryModule` which requires a database path. It can spawn threads if modules implement them and performs logging/error reporting via `ai.functions`.

- **Error Handling:** Extensive use of `try...except` blocks is present, particularly in loading methods (`_load_tool_module`, `_load_vector_memory_logic`, etc.). These blocks catch import errors, instantiation failures, and runtime exceptions during shutdown, logging them gracefully rather than crashing the registry.

## 4. Dependencies & Configuration
**Environment & Configuration:**
- `ProgramConfig` — Used throughout to check configuration settings (`*_ENABLED`, file paths, weights) to determine which modules should be loaded and how they should be initialized.

**Module Dependencies:**
- **Standard/External:** `typing`, `importlib`
- **Internal:** [EngineManager](/ai/services/engine_manager.md), [ProgramConfig](/ai/services/config_helper.md), [BaseModule](/ai/modules/base_module.md), [EngineType](/ai/entities/model_enums.md), [ai.functions](/ai/functions.md)