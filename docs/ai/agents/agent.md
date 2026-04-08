## 1. Architectural Role
This file is responsible for loading and validating the pipeline configuration JSON file, ensuring that all referenced prompt files exist.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `load_pipeline_config` | Function | Loads the pipeline configuration JSON file and validates the existence of referenced prompt files. |

## 3. Execution Logic & Flow
- **Initialization**: The function `load_pipeline_config` is called with a program object and a pipeline file path.
- **Data Path**: The function first constructs the full path to the pipeline file. It then reads the JSON file and parses it into a dictionary.
- **Conditional Branching**: The function checks if the prompt file specified for each agent exists. If a prompt file is missing, an error is logged, and the function returns an empty dictionary.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `json`
- **Internal Modules**: `functions as func`
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: None
- **Environment Lookups**: None