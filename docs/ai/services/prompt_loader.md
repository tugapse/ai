## Module Purpose
This file defines the `PromptLoader` class, which is responsible for locating, loading, and performing initial processing on system prompt files based on configuration settings.

## Interface & Exports
*   `class PromptLoader`: Manages the loading and processing of system prompt files.
    *   `staticmethod load_system_prompt(config: ProgramConfig, system_file_setting: str) -> str`: Reads and processes the content of a system prompt file, resolving its path either explicitly or within a configured templates directory.

## Internal Logic
The `load_system_prompt` method first retrieves the system templates directory from the provided `ProgramConfig`. It then attempts to resolve the system prompt file path by checking if `system_file_setting` is an explicit existing path. If not, it attempts to find the file (appending `.md` if necessary) within the `system_templates_dir`. If a file is found, its content is read using `func.read_file`. Warnings are logged if the file is not found or if the loaded content is empty. Finally, the loaded content is passed to a `TemplateInjection` instance, and its `replace_system_template()` method is called to process the template before returning the result.

## Dependencies
*   `os`
*   `pathlib.Path`
*   `typing.Optional`
*   `functions as func`
*   `config.ProgramConfig`
*   `config.ProgramSetting`
*   `core.template_injection.TemplateInjection`

## Constants & Environment
*   Hardcoded string: `".md"` (used for appending to template filenames).
*   No environment variable lookups identified in source.