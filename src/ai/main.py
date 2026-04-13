from importlib import util
import os
import sys

__version__ = "2.3.2"

import os
import sys
import importlib.util

def check_dependencies():
    """Diagnostic boot check for JARVIS dependencies."""
    # Format: (Package Name for UI, Import Name for check)
    core_deps = [
        ("colorama", "colorama"),
        ("python-dotenv", "dotenv"),
        ("huggingface-hub", "huggingface_hub"),
        ("prompt_toolkit", "prompt_toolkit"),
        ("requests", "requests"),
    ]
    
    # Platform-specific logic
    if sys.platform == "win32":
        core_deps.append(("pyreadline3", "pyreadline3"))
        core_deps.append(("triton-windows", "triton"))
    else:
        core_deps.append(("triton", "triton"))

    missing = [pkg for pkg, imp in core_deps if importlib.util.find_spec(imp) is None]

    if missing:
        # 1. Gather System Info
        py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Venv Detection
        is_venv = sys.prefix != sys.base_prefix
        venv_path = sys.prefix if is_venv else "None"
        
        # 2. UI Colors (Ubuntu Optimized)
        RED_B = "\033[91;1m"   # Bright Red Bold
        YLW_B = "\033[93;1m"   # Bright Yellow Bold
        WHITE = "\033[0m"      # Standard Terminal White
        BOLD  = "\033[1m"      # Bold White
        
        # 3. Stylized Diagnostic Output
        print(f"\n{RED_B}[!] SYSTEM REJECT: MISSING DEPENDENCIES{WHITE}")
        print(f"-----------------------------------------------------------")
        print(f"Python Version  : {WHITE}{py_ver}")
        print(f"Source Location : {WHITE}{script_dir}")
        print(f"Virtual Env     : {WHITE}{'Active' if is_venv else 'INACTIVE'}")
        if is_venv:
            print(f"Env Path        : {WHITE}{venv_path}")
        print(f"Missing Modules : {RED_B}{', '.join(missing)}{WHITE}")
        print(f"-----------------------------------------------------------")
        
        # 4. Context-Aware Instructions
        print(f"\n{YLW_B}[*] RESOLUTION:{WHITE}")
        if is_venv:
            print(f"    Your virtual environment is available. Please run:")
        else:
            print(f"    You are outside a virtual environment. Please run:")
        
        print(f"    {BOLD}source .venv/bin/activate && python dependency_installer.py{WHITE}")
        print(f"\n{WHITE}Exiting...")
        sys.exit(1)

# --- BOOT SEQUENCE START ---
check_dependencies()

import argparse
import warnings
import logging
from typing import Optional

# Core imports
from program import Program
from config import ProgramSetting
from entities.model_enums import ModelType
import functions as func
from color import Color 
from cli_args import CliArgs 


def hack_warnings():
    """Suppresses library-specific noise."""
    os.environ['TQDM_DISABLE'] = '1'
    os.environ['BITSANDBYTES_NOWELCOME'] = '1'
    os.environ["TRANSFORMERS_VERBOSITY"] = "error"
    logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
    logging.getLogger("huggingface_hub.utils._http").setLevel(logging.ERROR)
    warnings.filterwarnings("ignore", category=FutureWarning, module="bitsandbytes")
    warnings.filterwarnings("ignore", message=".*local_dir_use_symlinks.*")

def load_args() -> tuple[argparse.ArgumentParser, argparse.Namespace]:
    """Defines and parses EVERY flag expected by the CliArgs processor."""
    parser = argparse.ArgumentParser(description=f"JARVIS AI Assistant v{__version__}")
    
    # Core Chat Args
    parser.add_argument("--msg", "-m", type=str, help="Direct question", default=None)
    parser.add_argument("--model", "-md", type=str, help="Model config filename")
    parser.add_argument("--system", "-s", type=str, help="System prompt name")
    parser.add_argument("--system-file", "-sf", type=str, help="System prompt filename")
    parser.add_argument("--list-models", "-l", action="store_true", help="See available models")
    
    # File & Context Args
    parser.add_argument("--file", "-f", type=str, help="Load a file")
    parser.add_argument("--image", "-i", type=str, help="Load an image file")
    parser.add_argument("--load-folder", "-D", type=str, help="Load multiple files from folder")
    parser.add_argument("--ext", "-e", type=str, help="File extension for folder search")
    
    # Task & Automation Args
    parser.add_argument("--task", "-t", type=str, help="Template name")
    parser.add_argument("--task-file", "-tf", type=str, help="Template filename")
    parser.add_argument("--output-file", "-o", type=str, help="Output filename")
    parser.add_argument("--auto-task", "-at", type=str, help="JSON auto-task config")
    parser.add_argument("--agent", action="store_true", help='Use agent mode')
    parser.add_argument("--pipeline", "-ppl", type=str, help="Pipeline filename.json")
    parser.add_argument("--session-id", type=str, help="Set a session ID for agent memory to persist state.")
    
    # Display & Debug Args
    parser.add_argument("--print-chat", "-p", type=str, help="Print chat log")
    parser.add_argument("--print-log", "-pl", action="store_true", help='Print logs')
    parser.add_argument("--print-debug", "-pdb", action="store_true", help='Print debug info')
    parser.add_argument("--no-out", "-q", action="store_true", help='Quiet mode')
    parser.add_argument("--no-think-anim", "-nta", action="store_true", help='Disable thinking animation')
    parser.add_argument("--debug-console", "-dc", action="store_true", help='Disable console clearing')

    # Extra Modules
    parser.add_argument( "--modules",     nargs="+", help="Enable specific modules (e.g., --modules voice )",default=[]     )
    
    # System Args
    parser.add_argument("--install", help='Install/Update dependencies', action="store_true")

    # Config Generation Group
    config_group = parser.add_argument_group('Model Config Generation')
    config_group.add_argument('--generate-config', metavar='FILENAME', type=str)
    config_group.add_argument('--model-type', type=str, choices=[t.value for t in ModelType])

    return parser, parser.parse_args()

def print_chat_header(prog: Program) -> None:
    """Displays the stylized JARVIS boot header."""
    chat_name = prog.models.get_chat_name()
    func.set_console_title(f"JARVIS AI: {chat_name}")
    
    system_p_path = prog.config.get(ProgramSetting.SYSTEM_PROMPT_FILE)
    if system_p_path:
        system_name = os.path.basename(str(system_p_path)).replace(".md", "").replace("_", " ").capitalize()
    else:
        system_name = "Default"

    func.out(f"{Color.GREEN}# Starting {Color.YELLOW}{chat_name}{Color.GREEN} assistant")
    func.out(f"# Using {Color.YELLOW}{system_name}{Color.GREEN} logic system")
    func.out(f"{Color.RESET}--------------------------")

def check_dependencies():
    """Verifies required packages are installed before booting the system."""
    # Format: (Package Name for UI, Import Name for check)
    core_deps = [
        ("colorama", "colorama"),
        ("python-dotenv", "dotenv"),
        ("huggingface-hub", "huggingface_hub"),
        ("prompt_toolkit", "prompt_toolkit"),
        ("requests", "requests"),
    ]
    
    # Platform-specific checks
    if sys.platform == "win32":
        core_deps.append(("pyreadline3", "pyreadline3"))
        core_deps.append(("triton-windows", "triton"))
    else:
        core_deps.append(("triton", "triton"))

    missing = []
    for pkg_name, import_name in core_deps:
        if importlib.util.find_spec(import_name) is None:
            missing.append(pkg_name)

    if missing:
        # Standard ANSI colors used here as colorama might be missing
        RED = "\033[31m"
        YELLOW = "\033[33m"
        RESET = "\033[0m"
        
        print(f"{RED}[ ! ] Critical dependencies missing: {', '.join(missing)}{RESET}")
        print(f"{YELLOW}[ * ] Please run the installer script to fix this:{RESET}")
        print(f"\n      python dependency_installer.py\n")
        sys.exit(1)

     
def run():
    hack_warnings()
    prog: Program = Program()
    parser, args = load_args()
    
    try:
        
        prog.load_config(args=args) 
        
        if args.debug_console: 
            func.log("DEBUG MODE Enabled")
            func.ALLOW_CLEAR_CONSOLE = False
            func.LOCK_LOG = False 
            prog.config.set(ProgramSetting.PRINT_LOG, True)
            prog.config.set(ProgramSetting.PRINT_DEBUG, True)
        else:
            func.ALLOW_CLEAR_CONSOLE = (not args.print_log and not args.print_debug)
        

        
        prog.init_program(args)         
        
        cli_args_processor = CliArgs()
        cli_args_processor.parse_args(prog=prog, args=args, args_parser=parser)
        
        if func.ALLOW_CLEAR_CONSOLE: 
            func.clear_console()

        print_chat_header(prog=prog)
        
        prog.run()
        
    except KeyboardInterrupt:
        print("closing app")
    except Exception as e:
        # If in debug mode, show full traceback, otherwise show clean error
        is_debug = getattr(args, 'debug_console', False) if args else False
        if is_debug:
            import traceback
            traceback.print_exc()
        else:
            func.out(f"{Color.RED}[ ! ] Error: {e}{Color.RESET}") 
        sys.exit(1)
    finally:
        prog.shutdown()
        exit(0)
        

   
if __name__ == "__main__":
    # Ensure local module directory is in the sys path
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))
    run()