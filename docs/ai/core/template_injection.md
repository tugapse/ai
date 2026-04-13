

## 1. Architectural Role  
Injects templated content into system prompts by replacing placeholders with pre-configured template files.  

## 2. Interface & API Surface  
| Entity | Type | Functional Responsibility |  
| :--- | :--- | :--- |  
| `TemplateInjection` | Class | Manages template injection via system/task templates |  
| `replace_system_template` | Method | Replaces placeholders in system template with injected content |  
| `_load_injection_template` | Method | Loads template content from filesystem based on configuration |  
| `__init__` | Method | Initializes system and task templates |  

## 3. Execution Logic & Flow  
- **Initialization**: Sets `system_template` and `task_template` from constructor arguments.  
- **Data Path**: Input (`system_template`)  Processing (placeholder replacement via `INJECT_TEMPLATES` config)  Output (modified system template).  
- **Conditional Branching**: Checks if template file exists via `os.path.exists` before loading.  

## 4. Resource Dependencies  
- **Standard Libraries**: `os`, `functions`  
- **Internal Modules**: `config.ProgramConfig`, `config.ProgramSetting`  
- **External Packages**: None  

## 5. Configuration & Environment  
- **Hardcoded Constants**: `INJECT_TEMPLATES` (key in `ProgramConfig.current.config`).  
- **Environment Lookups**: `ProgramSetting.PATHS_INJECT_TEMPLATES` (directory path for templates).