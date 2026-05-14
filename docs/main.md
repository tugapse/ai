## 1. Architectural Role
Serves as the primary entry point and orchestration bootstrap for the JARVIS ecosystem, managing dependency validation, CLI argument parsing, and the lifecycle transition from system initialization to either a maintenance mode, a server instance, or an interactive agentic session.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `check_dependencies` | Func | Validates presence of required Python packages across OS platforms. |
| `hack_warnings` | Func | Configures environment variables and logging levels to suppress library noise. |
| `JarvisHelpFormatter` | Class | Custom `argparse` formatter for high-width, aligned help descriptions. |
| `load_args` | Func | Constructs the `argparse.ArgumentParser` and defines all command-line flag groups. |
| `print_chat_header` | Func | Renders the visual terminal header once a neural link is established. |
| `run` | Func | Executes the main application lifecycle: dependency check $\rightarrow$ config load $\rightarrow$ mode selection $\rightarrow$ execution. |

## 3. Execution Logic & Flow
- **Initialization**: 
    - Sets `sys.path` to include the local directory.
    - Defines global `__version__` and `__logo` constants.
    - Sets up signal handlers (`SIGINT`, `SIGTERM`) to trigger `prog.shutdown()` and garbage collection.
- **Data Path**: 
    - **Input**: Command-line arguments via `sys.argv`.
    - **Processing**: 
        1. `check_dependencies` scans `importlib.util.find_spec`.
        2. `load_args` parses raw strings into a `Namespace` object.
        3. `prog.load_config` and `prog.init_config` map arguments to `ProgramSetting` values.
        4. `CliArgs.parse_args` processes high-level logic based on parsed flags.
    - **Output**: Either a terminal-based interactive chat, a persistent Brain Server, or a maintenance execution (e.g., `--install`).
- **Conditional Branching**:
    - **Platform Check**: Branches dependency list based on `sys.platform == "win32"`.
    - **Maintenance Mode**: If `maintenance_keys` (e.g., `install`, `server`) are present in `args`, the system executes the specific task and exits via `sys.exit(0)`.
    - **Server Mode**: If `args.server` is true, enters an infinite `while True` loop to keep the thread alive.
    - **Debug Mode**: If `args.debug_console` is true, disables `func.ALLOW_CLEAR_CONSOLE` and forces verbose logging.

## 4. Resource Dependencies
- **Standard Libraries**: `os`, `sys`, `importlib.util`, `argparse`, `warnings`, `logging`, `traceback`, `time`, `signal`, `gc`, `typing`.
- **Internal Modules**: `program.Program`, `config.ProgramSetting`, `entities.model_enums.ModelType`, `functions` (as `func`), `color.Color`, `cli_args.CliArgs`.
- **External Packages**: `colorama`, `python-dotenv`, `huggingface-hub`, `prompt_toolkit`, `requests`.

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `__version__ = "3.1.1"`
    - `maintenance_keys = ['install', 'generate_config', 'server', 'print_chat', 'list_models', 'create_tool']`
- **Environment Lookups**:
    - `os.environ['TQDM_DISABLE']`
    - `os.environ['BITSANDBYTES_NOWELCOME']`
    - `os.environ["TRANSFORMERS_VERBOSITY"]`