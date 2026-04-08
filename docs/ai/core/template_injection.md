## Module Purpose
This file defines the `TemplateInjection` class, which is responsible for handling the injection of various templates into a base system prompt.

## Interface & Exports
- `TemplateInjection` (Class): Manages the process of replacing placeholders in a system template with content from other template files.

## Internal Logic
The `TemplateInjection` class initializes with a `system_template` and an optional `task_template`. The `replace_system_template` method retrieves a list of injection configurations from `ProgramConfig.current.config` using the key `"INJECT_TEMPLATES"`. It then iterates through this list, using each configuration's `value` to load a template file via `_load_injection_template`. The content of the loaded template replaces the corresponding `key` placeholder within the `system_template`. The `_load_injection_template` method constructs a file path by joining a directory obtained from `ProgramConfig.current.get(ProgramSetting.PATHS_INJECT_TEMPLATES)` with the provided `template_name` (ensuring a `.md` extension), checks for file existence, and reads the file content using `functions.read_file`.

## Dependencies
- `config` (imports `ProgramConfig`, `ProgramSetting`)
- `functions`
- `os`

## Constants & Environment
- Hardcoded string `"INJECT_TEMPLATES"` used as a key for configuration lookup in `ProgramConfig.current.config.get()`.
- Hardcoded string `".md"` used for file extension manipulation within `_load_injection_template`.
- `ProgramSetting.PATHS_INJECT_TEMPLATES` is used to retrieve a path from `ProgramConfig.current`.