## 1. Architectural Role
Ensures configuration consistency by merging a default JSON template into a user-defined configuration file while preserving existing user settings and utilizing atomic write operations to prevent data corruption.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `merge_json_configs` | Func | Orchestrates the loading, merging, and atomic saving of primary and default JSON configuration files. |

## 3. Execution Logic & Flow
- **Initialization**: 
    - Retrieves `AI_ASSISTANT_CONFIG_FILENAME` from environment variables.
    - Resolves `default_config_path` by joining the script's absolute directory with `config.json`.
- **Data Path**: 
    - **Input**: Reads `primary_file_path` (if exists) and `config_defaults_path`.
    - **Processing**: Performs a dictionary merge using `{**config_defaults, **primary_data}`, where `primary_data` keys overwrite `config_defaults` keys.
    - **Output**: Writes the merged dictionary to a `tempfile.NamedTemporaryFile` in the target directory, then performs an `os.replace` to the primary path.
- **Conditional Branching**:
    - **Primary File Existence**: If `primary_file_path` is missing, it initializes an empty dictionary instead of failing.
    - **JSON Validation**: If either file contains invalid JSON, the process triggers `sys.exit(1)`.
    - **Default File Existence**: If `config_defaults_path` is missing, the process triggers `sys.exit(1)`.
    - **Write Failure**: If an exception occurs during the save process, the temporary file is deleted and the process exits.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `json`, `sys`, `tempfile`
- **Internal Modules**: None
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `config.json`: The filename used for default settings relative to the script directory.
    - `indent=4`: Formatting for the output JSON file.
- **Environment Lookups**: 
    - `AI_ASSISTANT_CONFIG_FILENAME`: Defines the path to the primary user configuration file.