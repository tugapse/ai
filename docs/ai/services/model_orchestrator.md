

## 1. Architectural Role  
Manages model loading and configuration by resolving model config files, instantiating models via ModelManager, and initializing model parameters for downstream usage.  

## 2. Interface & API Surface  
| Entity | Type | Functional Responsibility |  
| :--- | :--- | :--- |  
| `ModelOrchestrator` | Class | Coordinates model loading, configuration, and parameter initialization |  
| `load` | Method | Loads model configuration, instantiates model, and initializes parameters |  
| `_init_model_params` | Method | Initializes model parameters from model options or defaults |  
| `get_params` | Method | Exposes model parameters as a dictionary |  
| `get_chat_name` | Method | Retrieves the model's chat name from configuration |  

## 3. Execution Logic & Flow  
- **Initialization**: Sets `config`, `llm` (None), `model_params` (empty dict), and `model_chat_name` ("__no_chat_name__").  
- **Data Path**:  
  1. Input: `model_config_name` and `system_prompt`   
  2. Processing: Resolves config file path, loads config via `ModelManager`, instantiates model, initializes parameters   
  3. Output: Returns `llm` instance.  
- **Conditional Branching**:  
  - Checks if `model_config_name` is empty and defaults to "default.json".  
  - Ensures filename ends with ".json".  
  - Fallbacks to local directory if `ProgramSetting.PATHS_MODEL_CONFIGS` is missing.  
  - Validates `ModelManager` returns a non-null model instance.  

## 4. Resource Dependencies  
- **Standard Libraries**: `os`, `sys`, `typing`  
- **Internal Modules**: `services.model_manager`, `core.llms.base_llm`, `config`  
- **External Packages**: None  

## 5. Configuration & Environment  
- **Hardcoded Constants**: `"default.json"`, `"__no_chat_name__"`  
- **Environment Lookups**: `ProgramSetting.PATHS_MODEL_CONFIGS` from `config`