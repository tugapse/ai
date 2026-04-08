## Module Purpose
This file defines the `ThinkingLogManager` class, which manages a log file for "thinking" content, providing exclusive write access across processes via a lock file mechanism while permitting concurrent reads.

## Interface & Exports
The primary class exported and intended for use by other modules is `ThinkingLogManager`.

## Internal Logic
The `ThinkingLogManager` class initializes by constructing log and lock file paths, prioritizing a base log directory from `ProgramConfig` if available, otherwise defaulting to a subdirectory within the user's home directory. It implements a file-based locking mechanism using `os.open` with `os.O_CREAT | os.O_EXCL` in `_acquire_write_lock` to ensure exclusive write access, with a polling mechanism to wait for lock availability. Writing methods like `write_thinking_log` and `write_session_header` acquire this lock, append content to both the specific log file and a default active log file, and then release the lock. The `read_thinking_log` method checks for the absence of the lock file, waiting briefly if present, before reading the log file's content to minimize reading inconsistent data.

## Dependencies
*   `os`
*   `time`
*   `errno`
*   `datetime`
*   `program` (specifically `ProgramConfig`, `ProgramSetting`)

## Constants & Environment
*   `DEFAULT_LOG_SUBDIR`: `os.path.join("Ai", "logs", "thinking")`
*   The class accesses `ProgramConfig.current.get(ProgramSetting.PATHS_LOGS)` to determine a base log directory.