

## 1. Architectural Role  
Loads and validates pipeline configuration JSON files, ensuring referenced prompt files exist and resolving their absolute paths.  

## 2. Interface & API Surface  
| Entity | Type | Functional Responsibility |  
| :--- | :--- | :--- |  
| `load_pipeline_config` | Function | Loads pipeline config JSON, resolves relative paths, verifies prompt file existence, and returns validated config |  

## 3. Execution Logic & Flow  
- **Initialization**: Appends project root to sys.path to ensure module resolution.  
- **Data Path**: Input `pipeline_file`  resolved to absolute path  loaded as JSON  agents' prompt files validated and path normalized.  
- **Conditional Branching**: Checks if pipeline file exists; if not, returns empty dict. Verifies each agent's prompt file existence; if missing, returns empty dict.  

## 4. Resource Dependencies  
- **Standard Libraries**: `os`, `sys`, `json`  
- **Internal Modules**: `functions`, `config`, `.tool_registry`, `.llm_connector`, `.message_orchestrator`  
- **External Packages**: None  

## 5. Configuration & Environment  
- **Hardcoded Constants**: `ProgramSetting.ROOT_DIRECTORY`  
- **Environment Lookups**: `prog.config.get(ProgramSetting.ROOT_DIRECTORY)`