

## 1. Architectural Role  
Manages model configuration lifecycle and engine installation verification to instantiate LLM models based on type and properties.  

## 2. Interface & API Surface  
| Entity | Type | Functional Responsibility |  
| :--- | :--- | :--- |  
| `ModelManager` | Class | Central hub for model configuration management and engine validation |  
| `is_engine_installed` | Static Method | Checks if a model engine is installed by querying `installed_engines.json` |  
| `generate_default_config` | Static Method | Creates default model configuration dictionaries for specified types |  
| `load_config` | Static Method | Parses and validates JSON model configuration files |  
| `save_config` | Static Method | Serializes model configuration dictionaries to JSON files |  
| `load_model_instance` | Static Method | Instantiates LLM models based on configuration, type, and system prompts |  

## 3. Execution Logic & Flow  
- **Initialization**: No explicit initialization; static methods are called directly.  
- **Data Path**:  
  1. `is_engine_installed` reads `installed_engines.json` to validate engine presence.  
  2. `load_config` parses JSON files into dictionaries for model properties.  
  3. `load_model_instance` maps model_type to LLM classes (HuggingFaceModel, T5Model, etc.), applies parameters, and instantiates objects.  
- **Conditional Branching**:  
  - Checks `model_type` to select appropriate LLM class.  
  - Validates engine installation via `installed_engines.json` before instantiation.  
  - Handles `quantization_bits`, `gguf_filename`, and vertex-specific logic for Gemini.  

## 4. Resource Dependencies  
- **Standard Libraries**: `os`, `json`, `sys`, `ctypes`  
- **Internal Modules**:  
  - `core.llms.base_llm` (BaseModel, ModelParams)  
  - `entities.model_enums` (ModelType, EngineType)  
  - `functions` (func.error, func.log)  
- **External Packages**: `colorama` (via `color` module)  

## 5. Configuration & Environment  
- **Hardcoded Constants**:  
  - `ModelType` to JSON ID mapping in `is_engine_installed`.  
  - Default model properties in `generate_default_config`.  
- **Environment Lookups**:  
  - `installed_engines.json` file path derived from `__file__`.  
  - `system_prompt` and `model_params` from input arguments.