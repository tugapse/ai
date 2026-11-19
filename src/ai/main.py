import os
import sys
import importlib.util
import argparse
import warnings
import logging
import traceback
import time
import signal
import gc
import re
from pathlib import Path

from ai.services.directory_manager import DirectoryManager
from ai.services.process_manager import ProcessManager

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Core imports
from ai.config import ProgramConfig, ProgramSetting
from ai.entities.model_enums import ModelType
import ai.functions as func
from ai.color import Color

def get_project_version() -> str:
    """
    Reads the project version from the pyproject.toml file.
    
    This function navigates up from the current file's directory to find
    the pyproject.toml file, reads its content, and extracts the version
    string. It provides a fallback version if the file or version key
    cannot be found.

    :return: The project version string or a fallback identifier.
    :rtype: str
    """
    try:
        bundle_root = getattr(sys, "_MEIPASS", None)
        if bundle_root:
            pyproject_path = Path(bundle_root) / "pyproject.toml"
        else:
            pyproject_path = Path(__file__).resolve().parent.parent.parent / "pyproject.toml"

        if not pyproject_path.exists():
            return "0.0.0-dev (pyproject.toml not found)"

        with open(pyproject_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Use regex to find version = "x.y.z"
        version_match = re.search(r'^version\s*=\s*"(.*?)"', content, re.MULTILINE)
        
        if version_match:
            return version_match.group(1)
        
        return "0.0.0-dev (version key not found)"
    except Exception:
        # Fallback version in case of any other error (e.g., parsing error)
        return "0.0.0-dev (fallback)"

__version__ = get_project_version()
__logo = func.get_logo_asci()

def check_dependencies():
    """
    Diagnostic boot check for JARVIS dependencies.

    Checks for the presence of core required Python modules. If any are missing,
    it prints an error message to the console and exits the program.
    """
    core_deps = [
        ("colorama", "colorama"),
        ("prompt_toolkit", "prompt_toolkit"),
        ("requests", "requests"),
    ]
    missing = [pkg for pkg, imp in core_deps if importlib.util.find_spec(imp) is None]

    if missing:
        RED_B = "\033[91;1m"
        YLW_B = "\033[93;1m"
        WHITE = "\033[0m"
        print(f"\n{RED_B}[!] SYSTEM REJECT: MISSING DEPENDENCIES{WHITE}")
        print(f"Missing Modules : {RED_B}{', '.join(missing)}{WHITE}")
        print(f"\n{YLW_B}[*] RESOLUTION: Run 'run.sh install'{WHITE}")
        sys.exit(1)

def hack_warnings():
    """
    Suppresses library-specific noise and warnings during runtime.

    Sets environment variables and configures logging/warnings filters
    to reduce console clutter from third-party libraries.
    """
    os.environ['TQDM_DISABLE'] = '1'
    os.environ['BITSANDBYTES_NOWELCOME'] = '1'
    os.environ["TRANSFORMERS_VERBOSITY"] = "error"
    logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
    warnings.filterwarnings("ignore", category=FutureWarning)
    # torchao (imported by transformers / sentence-transformers) registers an Enum with
    # torch's pytree, and newer torch logs a deprecation warning for it on every start.
    # A filter, not a level: torch may reset its loggers' levels when it configures logging.
    logging.getLogger("torch.utils._pytree").addFilter(_TorchPytreeEnumNoise())


class _TorchPytreeEnumNoise(logging.Filter):
    """Drops torch's 'register_constant() on Enum subclasses is deprecated' warning (not ours to fix)."""

    def filter(self, record: logging.LogRecord) -> bool:
        return "register_constant()" not in record.getMessage()

def load_args() -> tuple[argparse.ArgumentParser, argparse.Namespace]:
    """
    Parses the command line (see ``ai.cli``: one module per command group, each with its own
    ``--help``; the old top-level flags still work).

    :return: The ArgumentParser and the parsed Namespace.
    """
    description = f"""
  JUST A REASONING VIRTUAL INTELLIGENT SENTINEL AGENTIC INTERFACE
  Version: {__version__}

  My own JARVIS: chat, one-shot tasks, agents that work on your files, a Brain Server for
  your other devices. Run it with no arguments for the chat.

  {Color.CYAN}ai{Color.RESET}                              chat
  {Color.CYAN}ai -m "..."{Color.RESET}                     one message, then exit (add -f FILE, -t TASK, -o OUT...)
  {Color.CYAN}ai agent{Color.RESET}                        agents in this folder (ai agent --help)
"""
    if '-h' in sys.argv or '--help' in sys.argv:
        func.out(f"\n{__logo}")

    from ai.cli import parse_args
    return parse_args(version=__version__, description=description)



def _instance_mode(args, maintenance_keys) -> str:
    """What this instance is, as shown in the process registry."""
    if getattr(args, 'server', False):
        return "server"
    if any(getattr(args, key, None) for key in maintenance_keys):
        return "maintenance"
    if getattr(args, 'agent', False) or getattr(args, 'resume', None) is not None or getattr(args, 'pipeline', None):
        return "agent"
    return "chat"


def signal_exit_code(signum: int, serving: bool = False) -> int:
    """
    The exit code after a graceful shutdown on ``signum``: 128 + the signal number (130 for
    SIGINT, 143 for SIGTERM), the shell convention for "interrupted", so scripts can tell an
    interrupted run from a finished one. A server (or relay) exits 0: stopping it is its normal end.
    """
    return 0 if serving else 128 + int(signum)


def run():
    """
    Main execution function for the JARVIS system.

    Handles argument parsing, dependency checks, configuration loading,
    initialization of core managers (DirectoryManager, ProcessManager),
    and manages the main program loop or maintenance tasks.
    """
    parser, args = load_args()


    # debugging flags for development purposes
    # args.remote     = "http://0.0.0.0:9999"
    # args.list_sessions = True
    # args.model      = "gemini/gemini-25"
    # args.msg        = "explain this program"
    # args.agent      = True
    # args.overwrite_config = True
    # args.pipeline   = "gemini" 

    check_dependencies()
    hack_warnings()
    
    # Load configuration first, before any other imports that might rely on it
    ProgramConfig.load(args=args)
    
    # Now that config is loaded, we can safely import the main Program class
    from ai.program import Program

    prog = Program()
    prog.load_config(args=args) 
    is_server = getattr(args, 'server', False)

    def shutdown_handler(signum, frame):
        """
        Signal handler for graceful shutdown upon receiving SIGINT or SIGTERM.

        Calls the program's shutdown method, performs garbage collection, and exits with
        signal_exit_code: 130 (Ctrl+C) or 143 (SIGTERM) for an interrupted command, 0 for a
        server, whose stop is its normal end (``systemctl stop`` must not mark it failed).
        """
        func.log(f"\n{Color.YELLOW}[ * ] Signal {signum} received. Initiating graceful shutdown...{Color.RESET}")
        prog.shutdown()
        gc.collect()
        sys.exit(signal_exit_code(signum, serving=bool(is_server or getattr(args, "relay", None))))

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    if args.show_logo:
        func.log(f"\n{__logo}", start_line="")
    
    directory_manager = DirectoryManager()
    process_manager = ProcessManager(directory_manager)
    
    maintenance_keys = ['install',  'overwrite_config', 'generate_config', 'server', 'print_chat', 'list_models', 'create_tool', 'server_totp_setup', 'frontend', 'knowledge_list', 'knowledge_forget', 'list_sessions', 'mcp_action']
    ProcessManager.set_state("mode", _instance_mode(args, maintenance_keys))
    ProcessManager.set_state("activity", "starting")

    try:
        process_manager.start()  
        if getattr(args, 'debug_console', False): 
            func.ALLOW_CLEAR_CONSOLE = False
            prog.config.set(ProgramSetting.PRINT_LOG, True)
            prog.config.set(ProgramSetting.PRINT_DEBUG, True)
        else:
            func.ALLOW_CLEAR_CONSOLE = (not getattr(args, 'print_log', False) and not getattr(args, 'print_debug', False))
        # Maintenance modes (e.g. --server) exit before init_config, which sets these: without
        # this every func.log/func.debug reaches the console. func.out and func.error always do.
        debug_console = getattr(args, 'debug_console', False)
        func.LOCK_LOG = not (getattr(args, 'print_log', False) or debug_console)
        func.LOCK_DEBUG = not (getattr(args, 'print_debug', False) or debug_console)
        
        from ai.cli_args import CliArgs
        cli_args_processor = CliArgs()

        if any(getattr(args, key, None) for key in maintenance_keys):
            cli_args_processor.parse_args(prog=prog, args=args, args_parser=parser,directory_manager=directory_manager)
            if is_server:
                ProcessManager.set_state("activity", "online")
                func.out(f"{Color.GREEN}[  ] Neural Hub is online. Press Ctrl+C to shut down.{Color.RESET}")
                if prog.modules:
                    prog.modules.load_all()
            
            sys.exit(0) 
        
        prog.init_config(args=args)
        prog.init_program()

        cli_args_processor.parse_args(prog=prog, args=args, args_parser=parser,directory_manager=directory_manager)
        
        
        ProcessManager.set_state("activity", "ready")
        prog.run()
        
    except Exception as e:
        if not isinstance(e, (SystemExit, KeyboardInterrupt)):
            if getattr(args, 'debug_console', False):
                traceback.print_exc()
            else:
                func.out(f"{Color.RED}[ ! ] Error: {e}{Color.RESET}") 
            sys.exit(1)
    finally:
        if not is_server:
            prog.shutdown()
        process_manager.shutdown()

if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))
    run()