## Module Purpose
This file serves as the main entry point for the AI assistant application, responsible for parsing command-line arguments, initializing the core program, handling an installation routine, and orchestrating the application's execution flow.

## Interface & Exports
*   `run()`: The primary function executed when the script is run, initiating the application's lifecycle.
*   `__version__`: A string constant representing the application's version.

## Internal Logic
The file begins by suppressing various warnings from common libraries like `tqdm`, `bitsandbytes`, and `huggingface_hub` via `hack_warnings()` and `logging` configuration. It then dynamically adjusts `sys.path` to enable root-level imports. The `handle_install()` function checks for an `--install` flag; if present, it locates, dynamically loads, and executes an `install_engines.py` script from the project root before exiting. `load_args()` defines and parses a comprehensive set of command-line arguments for interacting with the AI assistant. `init_program_and_args()` initializes the main `Program` object, loading its configuration and setting up console behavior based on arguments. The `run()` function orchestrates these steps: loading arguments, checking for install, initializing the program, processing CLI arguments with `CliArgs`, clearing the console, printing a chat header, and finally invoking the `Program`'s main execution loop. It includes robust error handling for `KeyboardInterrupt` and general exceptions.

## Dependencies
*   `os`
*   `warnings`
*   `logging`
*   `sys`
*   `argparse`
*   `importlib.util`
*   `typing` (specifically `Optional`)
*   `program` (internal module, imports `Program`)
*   `config` (internal module, imports `ProgramConfig`, `ProgramSetting`)
*   `entities.model_enums` (internal module, imports `ModelType`)
*   `functions` (internal module, imports `func`)
*   `color` (internal module, imports `Color`)
*   `cli_args` (internal module, imports `CliArgs`)

## Constants & Environment
*   `__version__ = "2.2.0"`
*   Environment variables set:
    *   `TQDM_DISABLE = '1'`
    *   `BITSANDBYTES_NOWELCOME = '1'`
    *   `TRANSFORMERS_VERBOSITY = "error"`
*   Logging levels used: `logging.ERROR`
*   Warning categories filtered: `FutureWarning` (for `bitsandbytes`)
*   Warning messages filtered: `".*local_dir_use_symlinks.*"`