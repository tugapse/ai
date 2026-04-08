## Module Purpose
This file provides a suite of utility functions designed for an AI agent, enabling interactions with the file system, execution of shell commands, and sending system notifications. It standardizes path handling relative to a project root and offers tools for file manipulation, directory exploration, and content searching.

## Interface & Exports
The primary export is the dictionary `AVAILABLE_TOOLS`, which maps tool names to their corresponding functions:
*   `read_dir`
*   `read_file`
*   `write_file`
*   `patch_file`
*   `execute_command`
*   `send_notification`
*   `smart_search`

## Internal Logic
The module uses `_resolve_path` to convert `@ROOT` aliases and relative paths into absolute system paths, enforcing a security boundary within `PROJECT_ROOT`. `_sanitize_output_path` converts absolute paths back to `@ROOT` format for consistent agent output. `execute_command` runs shell commands, replacing `@ROOT` in the command string with the actual project root path. File operations like `read_dir`, `read_file`, `write_file`, and `patch_file` abstract common filesystem tasks. `smart_search` combines `os.walk` for filename matching and `grep` for content searching. `send_notification` uses `notify-send` for desktop alerts. All functions return a dictionary containing `status` and relevant data or error messages.

## Dependencies
*   `os`
*   `shutil`
*   `subprocess`
*   `requests`
*   `json`
*   `difflib`
*   `typing`
*   `functions as func`
*   `re`

## Constants & Environment
*   `PROJECT_ROOT`: A global constant initialized with `os.getcwd()`, serving as the base directory for all relative path operations.