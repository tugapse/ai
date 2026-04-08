## 1. Architectural Role
Handles file and directory operations, command execution, and smart search functionalities for an AI agent.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `send_notification` | Function | Sends a desktop notification to the user. |
| `_resolve_path` | Function | Resolves a path to an absolute system path, ensuring it's within the project boundaries. |
| `_sanitize_output_path` | Function | Converts an absolute system path back into the @ROOT format for the LLM. |
| `execute_command` | Function | Executes a shell command with @ROOT interpolation. |
| `read_dir` | Function | Explores a directory and returns lists of its child files and folders. |
| `read_file` | Function | Retrieves the full UTF-8 text content of a specific file. |
| `write_file` | Function | Creates or overwrites a file with the provided content. |
| `smart_search` | Function | Finds files using keyword or regex search. Inspects both names and content. |
| `patch_file` | Function | Surgically replaces a block of text within a file. |
| `AVAILABLE_TOOLS` | Dictionary | Registry of available tools. |

## 3. Execution Logic & Flow
- **Initialization**: No initialization required.
- **Data Path**:
  - **Input**: Command, path, search pattern, etc.
  - **Processing**: 
    - `send_notification`: Constructs and sends a notification.
    - `_resolve_path`: Cleans and resolves the path.
    - `_sanitize_output_path`: Converts the path back to @ROOT format.
    - `execute_command`: Interpolates @ROOT, executes the command, captures output.
    - `read_dir`: Lists directory contents.
    - `read_file`: Reads file content.
    - `write_file`: Writes content to a file.
    - `smart_search`: Searches for files and content.
    - `patch_file`: Searches for and replaces text in a file.
  - **Output**: Returns results or notifications.
- **Conditional Branching**:
  - `send_notification`: Checks for `notify-send` availability.
  - `_resolve_path`: Checks if the path is within project boundaries.
  - `execute_command`: Handles command execution errors.
  - `smart_search`: Fallback to simple substring match if regex is malformed.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `shutil`, `subprocess`, `requests`, `json`, `difflib`, `typing`
- **Internal Modules**: `functions as func`
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: `PROJECT_ROOT`
- **Environment Lookups**: None