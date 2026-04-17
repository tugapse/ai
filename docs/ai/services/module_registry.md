

## 1. Architectural Role  
Manages dynamic loading, unloading, and access to JARVIS modules via configuration-driven manifest execution.  

## 2. Interface & API Surface  
| Entity | Type | Functional Responsibility |  
| :--- | :--- | :--- |  
| `ModuleRegistry` | Class | Central registry for module lifecycle management |  
| `__init__` | Method | Initializes registry with configuration and empty module state |  
| `load_all` | Method | Loads all modules defined in the manifest based on config flags |  
| `load_module` | Method | Loads a specific module by name, updating config and active state |  
| `unload_module` | Method | Destroys a module instance, resets config, and cleans up resources |  
| `_load_voice_logic` | Method | Private loader for voice module with engine dependency check |  
| `get_voice` | Method | Legacy accessor for voice module instance |  
| `shutdown` | Method | Gracefully unloads all active modules and cleans up state |  

## 3. Execution Logic & Flow  
- **Initialization**: Sets `config` and `_active_modules` dictionary; initializes voice module loader in `_manifest`  
- **Data Path**: Config flags  manifest iteration  module loader execution  instance registration in `_active_modules`  
- **Conditional Branching**:  
  1. `config.get(config_key, False)` determines module activation  
  2. `name in _manifest` validates module existence  
  3. `hasattr(instance, 'shutdown')` triggers cleanup on unload  
  4. `ModelManager.is_engine_installed(...)` validates voice engine presence  

## 4. Resource Dependencies  
- **Standard Libraries**: `typing`, `os` (via `func.log`)  
- **Internal Modules**: `entities.model_enums`, `services.model_manager`, `config`, `functions`  
- **External Packages**: None explicitly referenced  

## 5. Configuration & Environment  
- **Hardcoded Constants**: `"VOICE_ENABLED"` (config key), `"voice"` (manifest key)  
- **Environment Lookups**: `self.config.get(...)` for module enablement flags