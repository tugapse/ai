## Module Purpose
This file is responsible for loading and validating a JSON-based pipeline configuration, ensuring that specified prompt files for agents within the pipeline exist and are correctly referenced. It also manages `sys.path` for module imports.

## Interface & Exports
- `load_pipeline_config(prog, pipeline_file: str)`: A function that loads, parses, and validates a pipeline configuration file.

## Internal Logic
The file first appends the directory of the current file to `sys.path`. The `load_pipeline_config` function takes a program object (`prog`) and a `pipeline_file` path. It resolves the `pipeline_file` path relative to `ProgramSetting.ROOT_DIRECTORY` if it's not absolute, then checks for its existence. Upon successful loading of the JSON configuration, it iterates through each agent defined in the configuration. For each agent, it verifies the existence of any specified `prompt_file` and stores its absolute path as `prompt_file_path` within the agent's data. Error handling is included for missing files and JSON parsing failures.

## Dependencies
- `os`
- `sys`
- `json`
- `functions` (imported as `func`)
- `config.ProgramSetting`
- `.tool_registry`
- `.llm_connector`
- `.message_orchestrator`

## Constants & Environment
None identified in source.