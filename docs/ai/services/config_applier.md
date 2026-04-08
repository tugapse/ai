## Module Purpose
This file defines the `ConfigApplier` class, which is responsible for applying command-line arguments parsed by `argparse` to a `ProgramConfig` instance, overriding default or loaded configuration settings.

## Interface & Exports
*   `ConfigApplier`: A class containing static methods to modify program configuration.
    *   `apply_cli_args_to_config(config: ProgramConfig, args: Optional[argparse.Namespace])`: A static method that takes a `ProgramConfig` object and an `argparse.Namespace` object, applying relevant CLI arguments to the configuration.

## Internal Logic
The `apply_cli_args_to_config` method checks for the presence of specific attributes in the `args` namespace:
1.  If `args.model` is present, it sets `ProgramSetting.MODEL_CONFIG_NAME` in `config`.
2.  If `args.system` is present, it constructs a filepath within the `system_templates_dir` using the argument value, ensuring it ends with `.md`. If the file exists, it sets `ProgramSetting.SYSTEM_PROMPT_FILE`. Otherwise, it logs a warning.
3.  If `args.system_file` is present, it uses the provided path directly. If the file exists, it sets `ProgramSetting.SYSTEM_PROMPT_FILE`. Otherwise, it logs a warning.
4.  If `args.print_log` is present, it sets `ProgramSetting.PRINT_LOG`.
5.  If `args.print_debug` is present, it sets `ProgramSetting.PRINT_DEBUG`.
6.  If `args.no_out` is present, it sets `ProgramSetting.PRINT_OUTPUT` to the inverse of `args.no_out`.
After applying CLI arguments, it updates `func.LOCK_LOG` and `func.LOCK_DEBUG` based on the final `ProgramSetting.PRINT_LOG` and `ProgramSetting.PRINT_DEBUG` values from the `config`.

## Dependencies
*   `os`
*   `argparse`
*   `typing`
*   `functions` (imported as `func`)
*   `config` (specifically `ProgramConfig`, `ProgramSetting`)

## Constants & Environment
*   Hardcoded string: `".md"` (used in path manipulation for `args.system`).
*   Hardcoded string: `level="WARNING"` (used in `func.log` calls).