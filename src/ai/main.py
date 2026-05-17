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
from typing import Optional
import re
from pathlib import Path

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
    """
    try:
        # Assumes pyproject.toml is at the project root, three levels up from src/ai/main.py
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
__logo = f"""{Color.CYAN}
      ██╗  █████╗  ██████╗  ██╗   ██╗ ██╗ ███████╗      █████╗  ██╗
      ██║ ██╔══██╗ ██╔══██╗ ██║   ██║ ██║ ██╔════╝     ██╔══██╗ ██║
      ██║ ███████║ ██████╔╝ ██║   ██║ ██║ ███████╗     ███████║ ██║
 ██   ██║ ██╔══██║ ██╔══██╗ ╚██╗ ██╔╝ ██║ ╚════██║     ██╔══██║ ██║
 ╚█████╔╝ ██║  ██║ ██║  ██║  ╚████╔╝  ██║ ███████║     ██║  ██║ ██║
  ╚════╝  ╚═╝  ╚═╝ ╚═╝  ╚═╝   ╚═══╝   ╚═╝ ╚══════╝     ╚═╝  ╚═╝ ╚═╝
{Color.RESET}"""

def check_dependencies():
    """Diagnostic boot check for JARVIS dependencies."""
    core_deps = [
        ("colorama", "colorama"),
        ("python-dotenv", "dotenv"),
        ("huggingface-hub", "huggingface_hub"),
        ("prompt_toolkit", "prompt_toolkit"),
        ("requests", "requests"),
    ]
    
    if sys.platform == "win32":
        core_deps.append(("pyreadline3", "pyreadline3"))
        core_deps.append(("triton-windows", "triton"))
    else:
        core_deps.append(("triton", "triton"))

    missing = [pkg for pkg, imp in core_deps if importlib.util.find_spec(imp) is None]

    if missing:
        RED_B = "\033[91;1m"
        YLW_B = "\033[93;1m"
        WHITE = "\033[0m"
        print(f"\n{RED_B}[!] SYSTEM REJECT: MISSING DEPENDENCIES{WHITE}")
        print(f"Missing Modules : {RED_B}{', '.join(missing)}{WHITE}")
        print(f"\n{YLW_B}[*] RESOLUTION: Run 'python main.py --install'{WHITE}")
        sys.exit(1)

def hack_warnings():
    """Suppresses library-specific noise."""
    os.environ['TQDM_DISABLE'] = '1'
    os.environ['BITSANDBYTES_NOWELCOME'] = '1'
    os.environ["TRANSFORMERS_VERBOSITY"] = "error"
    logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
    warnings.filterwarnings("ignore", category=FutureWarning)

class JarvisHelpFormatter(argparse.RawDescriptionHelpFormatter):
    def __init__(self, prog):
        # Increased max_help_position to 50 to keep descriptions aligned
        super().__init__(prog, max_help_position=50, width=110)

def load_args() -> tuple[argparse.ArgumentParser, argparse.Namespace]:
    """Defines and parses flags for the JARVIS ecosystem."""
    
    description=f"""

  JUST A REASONING VIRTUAL INTELLIGENT SENTINEL AGENTIC INTERFACE
  Version: {__version__}
  
  An integrated reasoning core powering autonomous agentic logic and long-term memory synthesis.
  
  {Color.CYAN}[ SYSTEM READY ] --------------------------------------------------------------------------{Color.RESET}
"""
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=JarvisHelpFormatter,
        usage=f"{Color.CYAN}ai{Color.RESET} [OPTIONS]",
        add_help=False,
        epilog=f"{Color.DIM}Sentinel monitoring active. Awaiting directive.{Color.RESET}"   
    )

    # 1. Cognitive Protocols (The Core Chat/Model flags)
    cog_group = parser.add_argument_group(f'{Color.CYAN}COGNITIVE PROTOCOLS{Color.RESET}')
    cog_group.add_argument("-h", "--help", action="help", help="Show this diagnostic help message")
    cog_group.add_argument("-v", "--version", action="version", version=f"JARVIS Version {__version__}", help="Display the system version and exit")
    cog_group.add_argument("--msg", "-m", type=str, help="Direct inquiry to the sentinel")
    cog_group.add_argument("--model", "-md", type=str, help="Specify neural model configuration")
    cog_group.add_argument("--system", "-s", type=str, help="Load named system persona") 
    cog_group.add_argument("--system-file", "-sf", type=str, help="Inject system prompt from disk")
    cog_group.add_argument("--list-models", "-l", action="store_true", help="Audit available neural models")

    # 2. Asset & Context Management
    asset_group = parser.add_argument_group(f'{Color.CYAN}ASSET & CONTEXT MANAGEMENT{Color.RESET}')
    asset_group.add_argument("--file", "-f", type=str, help="Analyze target file")
    asset_group.add_argument("--image", "-i", type=str, help="Process visual input from path")
    asset_group.add_argument("--load-folder", "-D", type=str, help="Ingest directory into vector memory")
    asset_group.add_argument("--ext", "-e", type=str, help="Filter context ingestion by extension")

    # 3. Autonomous Operations (Agentic Logic)
    agent_group = parser.add_argument_group(f'{Color.CYAN}AUTONOMOUS OPERATIONS{Color.RESET}')
    agent_group.add_argument("--agent", action="store_true", help="Enable stage-2 agentic logic injection")
    agent_group.add_argument("--task", "-t", type=str, help="Define autonomous directive")
    agent_group.add_argument("--task-file", "-tf", type=str, help="Load directive from file")
    agent_group.add_argument("--pipeline", "-ppl", type=str, help="Execute multi-stage instruction pipeline")
    agent_group.add_argument("--session-id", type=str, help="LTM (Long Term Memory) session key")
    agent_group.add_argument("--output-file", "-o", type=str, help="Designate clean output stream (temp-file mode)")

    # 4. Distributed Architecture
    net_group = parser.add_argument_group(f'{Color.CYAN}DISTRIBUTED ARCHITECTURE{Color.RESET}')
    net_group.add_argument("--server", action="store_true", help="Initialize Brain Server module")
    net_group.add_argument("--remote", "-r", type=str, help="Connect to remote neural hub URL")
    net_group.add_argument("--modules", nargs="+", default=[], help="Load specific server sub-modules")

    # 5. System Debug & Maintenance
    sys_group = parser.add_argument_group(f'{Color.CYAN}SYSTEM DEBUG & MAINTENANCE{Color.RESET}')
    sys_group.add_argument("--show-logo", action="store_true", help="Display the JARVIS startup logo")
    sys_group.add_argument("--print-chat", "-p", type=str, help="Output session history")
    sys_group.add_argument("--print-log", "-pl", action="store_true", help="Enable system telemetry logs")
    sys_group.add_argument("--print-debug", "-pdb", action="store_true", help="Enable verbose debug stream")
    sys_group.add_argument("--no-out", "-q", action="store_true", help="Quiet mode (suppress terminal output)")
    sys_group.add_argument("--no-think-anim", "-nta", action="store_true", help="Disable reasoning animations")
    sys_group.add_argument("--debug-console", "-dc", action="store_true", help="Lock console (disable clear-screen)")
    sys_group.add_argument("--install", action="store_true", help="Execute dependency sync protocol")
    sys_group.add_argument("--overwrite-config", action="store_true", help="Force configuration override")
    sys_group.add_argument("--create-tool", type=str, metavar='TOOL_NAME', help="Create a new user tool skeleton file")

    # 6. Model Generation (Your existing group)
    config_group = parser.add_argument_group(f'{Color.CYAN}MODEL CONFIG GENERATION{Color.RESET}')
    config_group.add_argument('--generate-config', metavar='FILENAME', type=str, help="Generate new model manifest")
    config_group.add_argument('--model-type', type=str, choices=[t.value for t in ModelType], help="Target architecture for manifest")

    if '-h' in sys.argv or '--help' in sys.argv:
        func.log(f"\n{__logo}", start_line="")

    return parser, parser.parse_args()

def print_chat_header(prog) -> None:
    chat_name = prog.models.get_chat_name() 
    
    if func.ALLOW_CLEAR_CONSOLE:
        func.clear_console()
        
    func.out(f"{Color.CYAN} # {Color.RESET}Established neural link to: {Color.CYAN}{chat_name}{Color.RESET}")
    func.out(f"{Color.CYAN} #{Color.PURPLE} Sentinel status: ACTIVE | Logic: INJECTED{Color.RESET}")
    func.out(f"{Color.CYAN} # {Color.RESET}-----------------------------------------------------------")


def run():
    parser, args = load_args()
    
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
        func.log(f"\n{Color.YELLOW}[ * ] Signal {signum} received. Initiating graceful shutdown...{Color.RESET}")
        prog.shutdown()
        gc.collect()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    if args.show_logo:
        func.log(f"\n{__logo}", start_line="")

    try:
        if getattr(args, 'debug_console', False): 
            func.ALLOW_CLEAR_CONSOLE = False
            prog.config.set(ProgramSetting.PRINT_LOG, True)
            prog.config.set(ProgramSetting.PRINT_DEBUG, True)
        else:
            func.ALLOW_CLEAR_CONSOLE = (not getattr(args, 'print_log', False) and not getattr(args, 'print_debug', False))
        
        from ai.cli_args import CliArgs
        cli_args_processor = CliArgs()

        maintenance_keys = ['install', 'generate_config', 'server', 'print_chat', 'list_models', 'create_tool']
        if any(getattr(args, key, None) for key in maintenance_keys):
            cli_args_processor.parse_args(prog=prog, args=args, args_parser=parser)
            if is_server:
                func.log(f"{Color.GREEN}[  ] Neural Hub is online. Press Ctrl+C to shut down.{Color.RESET}")
                if prog.modules:
                    prog.modules.load_all()
                while True:
                    time.sleep(1)
            
            sys.exit(0) 
        prog.init_config(args=args)

        prog.init_program()

        # Define arguments that imply a one-shot command instead of an interactive session.
        oneshot_args = [
            'msg', 'file', 'image', 'load_folder', 'task', 'task_file', 'pipeline'
        ]
        # Check if any one-shot argument was explicitly passed by the user BEFORE CliArgs processing.
        is_oneshot_command = any(getattr(args, arg, None) is not None for arg in oneshot_args)

        cli_args_processor.parse_args(prog=prog, args=args, args_parser=parser)
        
        # If a one-shot command was given, the program can now exit.
        if is_oneshot_command:
            sys.exit(0)
        
        # Otherwise, no one-shot command was given, so start the main interactive loop.
        if func.ALLOW_CLEAR_CONSOLE: 
            func.clear_console()

        print_chat_header(prog=prog)
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

if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))
    run()