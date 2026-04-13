

## 1. Architectural Role  
Utility functions for file operations, logging, console control, and directory management.  

## 2. Interface & API Surface  
| Entity | Type | Functional Responsibility |  
| :--- | :--- | :--- |  
| `set_console_title` | Func | Sets console title across OS platforms. |  
| `clear_console` | Func | Clears console output based on OS. |  
| `beep_console` | Func | Triggers console beep for attention. |  
| `get_files` | Func | Recursively searches files in a directory with optional extension filtering. |  
| `read_file` | Func | Reads file contents with UTF-8 encoding and error handling. |  
| `write_to_file` | Func | Writes content to a file with directory creation and error handling. |  
| `format_execution_time` | Func | Converts elapsed time to HH:MM:SS format. |  
| `get_root_directory` | Func | Retrieves configured root directory or fallback path. |  
| `ensure_directory_exists` | Func | Creates directories recursively with error logging. |  
| `error` | Func | Logs and outputs error messages with formatting. |  
| `log` | Func | Logs informational messages with file and console output. |  
| `debug` | Func | Logs debug messages with conditional output. |  
| `out` | Func | Outputs user-facing messages to stdout. |  
| `get_formatted_text` | Func | Applies color formatting to log messages based on severity. |  

## 3. Execution Logic & Flow  
- **Initialization**: Sets constants (`FILE_MODE_APPEND`, `FILE_MODE_CREATE`, `LOCK_LOG`, `LOCK_DEBUG`) and imports dependencies.  
- **Data Path**:  
  1. **Input**: User-provided directory and extension.  
  2. **Processing**: Uses `Path.rglob` to find files, validates existence, and constructs `ContextFile` objects.  
  3. **Output**: Returns list of `ContextFile` objects or exits on errors.  
- **Conditional Branching**:  
  - Checks directory existence in `get_files`.  
  - Validates file existence in `read_file` and `write_to_file`.  
  - Handles exceptions and exits on critical errors.  

## 4. Resource Dependencies  
- **Standard Libraries**: `os`, `sys`, `glob`, `pathlib`, `colorama`, `config`.  
- **Internal Modules**: `core.context_file`, `core.template_injection`, `ProgramConfig`.  
- **External Packages**: `colorama` (for colored output), `config` (for program settings).  

## 5. Configuration & Environment  
- **Hardcoded Constants**:  
  - `FILE_MODE_APPEND`, `FILE_MODE_CREATE`, `LOCK_LOG`, `LOCK_DEBUG`, `ALLOW_CLEAR_CONSOLE`.  
- **Environment Lookups**:  
  - `ProgramConfig.current` for root directory configuration.  
  - `os.path` and `os` for filesystem operations.