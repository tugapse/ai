

## 1. Architectural Role  
Loads and processes system prompt files, resolving paths from configuration or explicit input, then applies template injections to generate final prompt content.  

## 2. Interface & API Surface  
| Entity | Type | Functional Responsibility |  
| :--- | :--- | :--- |  
| `PromptLoader.load_system_prompt` | Function | Reads system prompt content from specified file path or templates directory, applies template replacements, and returns processed text. |  

## 3. Execution Logic & Flow  
- **Initialization**: No instance initialization; class is loaded with static method `load_system_prompt`.  
- **Data Path**: Input (`system_file_setting`)  Check explicit path existence  Fallback to templates directory (appending `.md` if missing)  Read file content  Apply `TemplateInjection.replace_system_template()`  Output processed prompt.  
- **Conditional Branching**:  
  1. Check if `system_file_setting` exists as explicit path.  
  2. If not, check if templates directory exists and construct path with `.md` suffix.  
  3. Log warning if file not found at any location.  
  4. Log warning if final content is empty.  

## 4. Resource Dependencies  
- **Standard Libraries**: `os`, `pathlib`, `typing`  
- **Internal Modules**: `functions`, `config`, `core.template_injection`  
- **External Packages**: None  

## 5. Configuration & Environment  
- **Hardcoded Constants**: `ProgramSetting.PATHS_SYSTEM_TEMPLATES`  
- **Environment Lookups**: `config.get(ProgramSetting.PATHS_SYSTEM_TEMPLATES)` via `ProgramConfig`