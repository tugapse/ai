import os
import sys
import importlib.util
import argparse
import warnings
import logging
import traceback
from typing import Optional

# Core imports
from program import Program
from config import ProgramSetting
from entities.model_enums import ModelType
import functions as func
from color import Color 
from cli_args import CliArgs 

__version__ = "2.3.2"

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

def load_args() -> tuple[argparse.ArgumentParser, argparse.Namespace]:
    """Defines and parses EVERY flag expected by the CliArgs processor."""
    parser = argparse.ArgumentParser(description=f"JARVIS AI Assistant v{__version__}")
    
    # Architecture & Networking
    net_group = parser.add_argument_group('Distributed Architecture')
    net_group.add_argument("--server", action="store_true", help="Start Brain Server")
    net_group.add_argument("--remote", "-r", type=str, help="Connect to Remote Brain URL")
    
    # Core Chat Args
    parser.add_argument("--msg", "-m", type=str, help="Direct question")
    parser.add_argument("--model", "-md", type=str, help="Model config")
    
    # --- ADDED THIS LINE ---
    parser.add_argument("--system", "-s", type=str, help="System prompt name (template)") 
    
    parser.add_argument("--system-file", "-sf", type=str, help="System prompt file (direct path)")
    parser.add_argument("--list-models", "-l", action="store_true")
    
    # File Context
    parser.add_argument("--file", "-f", type=str)
    parser.add_argument("--image", "-i", type=str)
    parser.add_argument("--load-folder", "-D", type=str)
    parser.add_argument("--ext", "-e", type=str)
    
    # Agent & Tasks
    parser.add_argument("--task", "-t", type=str)
    parser.add_argument("--task-file", "-tf", type=str)
    parser.add_argument("--output-file", "-o", type=str)
    parser.add_argument("--agent", action="store_true")
    parser.add_argument("--pipeline", "-ppl", type=str)
    parser.add_argument("--session-id", type=str)
    
    # UI & Debug
    parser.add_argument("--print-chat", "-p", type=str)
    parser.add_argument("--print-log", "-pl", action="store_true")
    parser.add_argument("--print-debug", "-pdb", action="store_true")
    parser.add_argument("--no-out", "-q", action="store_true")
    parser.add_argument("--no-think-anim", "-nta", action="store_true")
    parser.add_argument("--debug-console", "-dc", action="store_true")
    parser.add_argument("--modules", nargs="+", default=[])
    
    # System
    parser.add_argument("--install", action="store_true")
    config_group = parser.add_argument_group('Model Config Generation')
    config_group.add_argument('--generate-config', metavar='FILENAME', type=str)
    config_group.add_argument('--model-type', type=str, choices=[t.value for t in ModelType])

    return parser, parser.parse_args()

def print_chat_header(prog: Program) -> None:
    chat_name = prog.models.get_chat_name()
    func.out(f"{Color.GREEN}# Starting {Color.YELLOW}{chat_name}{Color.GREEN} assistant")
    func.out(f"{Color.RESET}--------------------------")

def run():
    check_dependencies()
    hack_warnings()
    
    prog = Program()
    parser, args = load_args()
    
    try:
        # 1. Load basic config
        prog.load_config(args=args) 
        
        # 2. Debug Setup
        if getattr(args, 'debug_console', False): 
            func.ALLOW_CLEAR_CONSOLE = False
            prog.config.set(ProgramSetting.PRINT_LOG, True)
            prog.config.set(ProgramSetting.PRINT_DEBUG, True)
        else:
            func.ALLOW_CLEAR_CONSOLE = (not getattr(args, 'print_log', False) and not getattr(args, 'print_debug', False))
        
        cli_args_processor = CliArgs()

        # 3. THE MAINTENANCE GATE (Safe Check)
        # Using getattr prevents the 'Namespace' attribute error if a flag is missing
        maintenance_keys = ['install', 'generate_config', 'server', 'print_chat', 'list_models']
        if any(getattr(args, key, None) for key in maintenance_keys):
            cli_args_processor.parse_args(prog=prog, args=args, args_parser=parser)
            sys.exit(0) 

        # 4. Full Initialization
        prog.init_program(args)         
        
        # 5. Execution Dispatch
        cli_args_processor.parse_args(prog=prog, args=args, args_parser=parser)
        
        if func.ALLOW_CLEAR_CONSOLE: 
            func.clear_console()

        print_chat_header(prog=prog)
        prog.run()
        
    except (SystemExit, KeyboardInterrupt):
        # Graceful exit for maintenance or Ctrl+C
        pass
    except Exception as e:
        if getattr(args, 'debug_console', False):
            import traceback
            traceback.print_exc()
        else:
            func.out(f"{Color.RED}[ ! ] Error: {e}{Color.RESET}") 
        sys.exit(1)
    finally:
        prog.shutdown()
        os._exit(0)

if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))
    run()