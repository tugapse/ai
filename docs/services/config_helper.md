## 1. Architectural Role
Acts as a configuration bridge that overrides existing `ProgramConfig` settings using values parsed from command-line arguments.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `CliConfig` | Class | Container for static methods to apply CLI overrides. |
| `apply_cli_args_to_config` | Static Method | Orchestrates the mapping of `argparse.Namespace` attributes to `ProgramConfig` settings and updates global logging locks. |

## 3. Execution Logic & Flow
- **Initialization**: No instance state is maintained; the class functions as a stateless utility provider.
- **Data Path**: `argparse.Namespace` (Input) $\rightarrow$ Attribute validation/existence checks $\rightarrow$ `ProgramConfig.set()` calls $\rightarrow$ Global `func.LOCK_LOG`/`func.LOCK_DEBUG` updates (Output).
- **Conditional Branching**:
    - **Null Check**: If `args` is `None`, execution terminates immediately.
    - **Model Override**: If `args.model` is present, updates `ProgramSetting.MODEL_CONFIG_NAME`.
    - **System Template Resolution**: 
        - If `args.system` is provided: Resolves path via `ProgramSetting.PATHS_SYSTEM_TEMP_LATES` or `func.get_root_directory()`, appends `.md`, and validates file existence before setting `ProgramSetting.SYSTEM_PROMPT_FILE`.
        - If `args.system_file` is provided: Validates direct path existence before setting `ProgramSetting.SYSTEM_PROMPT_FILE`.
    - **Boolean/Flag Overrides**: Checks existence of `print_log`, `print_debug`, and `no_out` attributes to update corresponding `ProgramSetting` values.
    - **Global State Synchronization**: Finalizes by setting `func.LOCK_LOG` and `func.LOCK_DEBUG` based on the newly applied configuration.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `argparse`
- **Internal Modules**: `functions` (as `func`), `program` (`ProgramConfig`, `ProgramSetting`)
- **External Packages**: None

## 5. Configuration & Environment
- **Hardcoded Constants**: `".md"` (file extension suffix).
- **Environment Lookups**: `config.get(ProgramSetting.PATHS_SYSTEM_TEMP_LATES)`, `func.get_root_directory()`.