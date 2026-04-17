

## 1. Architectural Role  
Central entry point for parsing CLI arguments, initializing the AI program, and orchestrating the main execution flow.  

## 2. Interface & API Surface  
| Entity | Type | Functional Responsibility |  
| :--- | :--- | :--- |  
| `hack_warnings` | Func | Suppresses library-specific warnings and logging verbosity |  
| `load_args` | Func | Defines and parses all CLI flags for the program |  
| `print_chat_header` | Func | Displays stylized JARVIS boot header with chat name and system prompt |  
| `run` | Func | Main execution flow: argument parsing  program initialization  CLI instruction processing  UI setup  main loop |  

## 3. Execution Logic & Flow  
- **Initialization**: Loads `main.py` and inserts local module path into `sys.path`.  
- **Data Path**: CLI args  parsed by `load_args`  passed to `Program.load_config`  processed by `CliArgs.parse_args`  routed to `prog.run` for execution.  
- **Conditional Branching**:  
  - Debug mode check (`args.debug_console`) enables verbose logging and disables console clearing.  
  - Exception handling differentiates between `KeyboardInterrupt` (clean exit) and general errors (debug output vs. user-facing error).  

## 4. Resource Dependencies  
- **Standard Libraries**: `os`, `sys`, `argparse`, `warnings`, `logging`, `typing`  
- **Internal Modules**: `program`, `config`, `functions`, `color`, `cli_args`  
- **External Packages**: `colorama` (via `Color` class), `bitsandbytes`, `transformers`  

## 5. Configuration & Environment  
- **Hardcoded Constants**:  
  - `__version__ = "3.0.1"`  
  - Environment variables in `hack_warnings` (`TQDM_DISABLE`, `BITSANDBYTES_NOWELCOME`, `TRANSFORMERS_VERBOSITY`)  
- **Environment Lookups**:  
  - `os.getenv` not explicitly used; config keys accessed via `prog.config.get(ProgramSetting.SYSTEM_PROMPT_FILE)`