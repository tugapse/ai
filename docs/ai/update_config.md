

## 1. Architectural Role  
Merge a primary JSON configuration file with a default configuration, preserving existing settings and adding missing defaults.  

## 2. Interface & API Surface  
| Entity | Type | Functional Responsibility |  
| :--- | :--- | :--- |  
| `merge_json_configs` | Func | Merges primary JSON config with default config, prioritizing primary data for overlapping keys. |  

## 3. Execution Logic & Flow  
- **Initialization**: Loads environment variable `AI_ASSISTANT_CONFIG_FILENAME` and determines script directory.  
- **Data Path**:  
  1. Load primary JSON (or create empty if missing).  
  2. Load default config (fails if missing).  
  3. Merge defaults into primary (primary overrides defaults).  
  4. Write merged JSON to primary file via temporary file.  
- **Conditional Branching**:  
  - Check existence of primary file (create empty if missing).  
  - Validate JSON syntax during load.  
  - Fail on missing default config file.  
  - Atomic write via temporary file to prevent corruption.  

## 4. Resource Dependencies  
- **Standard Libraries**: `os`, `json`, `sys`, `tempfile`  
- **Internal Modules**: None  
- **External Packages**: None  

## 5. Configuration & Environment  
- **Hardcoded Constants**: `config.json` in script directory.  
- **Environment Lookups**: `AI_ASSISTANT_CONFIG_FILENAME` for primary config path.