

## 1. Architectural Role  
Manages concurrent-safe logging of thinking processes with session headers and lock-based file access control.  

## 2. Interface & API Surface  
| Entity | Type | Functional Responsibility |  
| :--- | :--- | :--- |  
| `ThinkingLogManager` | Class | Central coordinator for writing/reading thinking logs with lock mechanisms |  
| `__init__` | Method | Initializes log file paths, directories, and lock configuration |  
| `write_thinking_log` | Method | Appends content to both session-specific and active log files |  
| `write_session_header` | Method | Writes session start headers with timestamp and tags to logs |  
| `read_thinking_log` | Method | Retrieves contents of the session-specific log file |  

## 3. Execution Logic & Flow  
- **Initialization**:  
  1. Sets `max_lock_wait_time` and `lock_poll_interval` from parameters.  
  2. Resolves `log_file_name` via fallback to `DEFAULT_FILENAME` if None.  
  3. Sanitizes filename by replacing spaces with underscores and ensuring `.log` extension.  
  4. Determines log directory via `ProgramConfig.current` or default user path.  
  5. Creates directory structure and resolves active log file path.  

- **Data Path**:  
  Input (content)  `_acquire_write_lock` (lock acquisition)  `write_thinking_log` (file append)  `_release_write_lock` (lock release).  

- **Conditional Branching**:  
  1. `_acquire_write_lock`: Checks for lock file existence and handles timeout.  
  2. `write_session_header`: Overwrites active log file instead of appending.  
  3. `read_thinking_log`: Returns empty string if file does not exist.  

## 4. Resource Dependencies  
- **Standard Libraries**: `os`, `time`, `errno`, `datetime`  
- **Internal Modules**: `config` (ProgramConfig, ProgramSetting)  
- **External Packages**: None  

## 5. Configuration & Environment  
- **Hardcoded Constants**:  
  - `DEFAULT_LOG_SUBDIR` = `"Ai/logs/thinking"`  
  - `DEFAULT_FILENAME` = `"thinking_process.log"`  
- **Environment Lookups**:  
  - `ProgramConfig.current.get(ProgramSetting.PATHS_LOGS)` (internal config access)