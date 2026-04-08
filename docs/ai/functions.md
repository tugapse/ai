## Module Purpose
This file centralizes utility functions for console management, file system operations including reading, writing, and directory creation, execution time formatting, and a structured logging system. It provides core operational capabilities for an AI application, integrating with a `ProgramConfig` for dynamic settings.

## Interface & Exports
*   `set_console_title(title)`
*   `clear_console()`
*   `beep_console()`
*   `get_files(directory, extension=None) -> list[ContextFile]`
*   `read_file(filename)`
*   `write_to_file(filename, content, filemode=FILE_MODE_CREATE, silent=False)`
*   `format_execution_time(start_time, end_time)`
*   `get_root_directory() -> str`
*   `ensure_directory_exists(path: str, silent=False)`
*   `error(text, start_line="[ * ]", level="ERROR", **kargs)`
*   `log(text, start_line="[ * ]", level="INFO", **kargs)`
*   `debug(text, start_line="[ # ]", level="DEBUG", **kargs)`
*   `out(text, level="INFO", **kargs)`
*   `get_formatted_text(text, level="INFO", start_line="[ * ]")`
*   `FILE_MODE_APPEND`
*   `FILE_MODE_CREATE`
*   `LOCK_LOG`
*   `LOCK_DEBUG`
*   `ACTIVE_LOG_FILENAME`
*   `SESSION_LOG_FILENAME`
*   `ALLOW_CLEAR_CONSOLE`

## Internal Logic
The module defines functions to interact with the console, such as setting the title and clearing the screen. File system logic includes recursively finding files within a directory using `pathlib.Path.rglob`, reading file contents, and writing content to files, ensuring parent directories exist via `os.makedirs`. Error conditions during file operations typically result in program exit. Time differences are formatted into `HH:MM:SS`. A root directory is determined from `ProgramConfig.current` or defaults to `~/Ai`. Logging (`log`, `debug`, `error`) and general output (`out`) functions format messages with color based on `level` and `start_line` using `get_formatted_text`, print to `stdout`/`stderr`, and optionally write to `ACTIVE_LOG_FILENAME` and `SESSION_LOG_FILENAME` based on `LOCK_LOG` and `LOCK_DEBUG` flags.

## Dependencies
*   `color.Color`
*   `color.pformat_text`
*   `os`
*   `pathlib.Path`
*   `sys`
*   `glob`
*   `core.context_file.ContextFile`
*   `core.template_injection.TemplateInjection`
*   `colorama.Fore`
*   `colorama.Style`
*   `config.ProgramConfig`
*   `config.ProgramSetting`

## Constants & Environment
*   `FILE_MODE_APPEND = "a"`
*   `FILE_MODE_CREATE = "w"`
