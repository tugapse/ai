import os
import sys
import importlib.util
import argparse
import warnings
import logging
import traceback
import time
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
    """Defines and parses flags for the JARVIS ecosystem."""
    parser = argparse.ArgumentParser(description=f"JARVIS AI Assistant v{__version__}")
    
    net_group = parser.add_argument_group('Distributed Architecture')
    net_group.add_argument("--server", action="store_true", help="Start Brain Server")
    net_group.add_argument("--remote", "-r", type=str, help="Connect to Remote Brain URL")
    
    parser.add_argument("--msg", "-m", type=str, help="Direct question")
    parser.add_argument("--model", "-md", type=str, help="Model config")
    parser.add_argument("--system", "-s", type=str, help="System prompt name") 
    parser.add_argument("--system-file", "-sf", type=str, help="System prompt file")
    parser.add_argument("--list-models", "-l", action="store_true")
    
    parser.add_argument("--file", "-f", type=str)
    parser.add_argument("--image", "-i", type=str)
    parser.add_argument("--load-folder", "-D", type=str)
    parser.add_argument("--ext", "-e", type=str)
    
    parser.add_argument("--task", "-t", type=str)
    parser.add_argument("--task-file", "-tf", type=str)
    parser.add_argument("--output-file", "-o", type=str)
    parser.add_argument("--agent", action="store_true")
    parser.add_argument("--pipeline", "-ppl", type=str)
    parser.add_argument("--session-id", type=str)
    
    parser.add_argument("--print-chat", "-p", type=str)
    parser.add_argument("--print-log", "-pl", action="store_true")
    parser.add_argument("--print-debug", "-pdb", action="store_true")
    parser.add_argument("--no-out", "-q", action="store_true")
    parser.add_argument("--no-think-anim", "-nta", action="store_true")
    parser.add_argument("--debug-console", "-dc", action="store_true")
    parser.add_argument("--modules", nargs="+", default=[])
    
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
    
    # Track if we are in server mode to prevent premature exit
    is_server = getattr(args, 'server', False)
    
    try:
        prog.load_config(args=args) 
        
        if getattr(args, 'debug_console', False): 
            func.ALLOW_CLEAR_CONSOLE = False
            prog.config.set(ProgramSetting.PRINT_LOG, True)
            prog.config.set(ProgramSetting.PRINT_DEBUG, True)
        else:
            func.ALLOW_CLEAR_CONSOLE = (not getattr(args, 'print_log', False) and not getattr(args, 'print_debug', False))
        
        cli_args_processor = CliArgs()

        # 3. THE MAINTENANCE GATE
        maintenance_keys = ['install', 'generate_config', 'server', 'print_chat', 'list_models']
        if any(getattr(args, key, None) for key in maintenance_keys):
            cli_args_processor.parse_args(prog=prog, args=args, args_parser=parser)
            
            # If we started the server, we enter a "Hold" pattern
            if is_server:
                while True:
                    time.sleep(1) # Keep the main thread alive
            
            # For other maintenance tasks (install, list), we exit normally
            sys.exit(0) 

        # 4. Full Local Initialization
        prog.init_program(args)         
        
        # 5. Execution Dispatch
        cli_args_processor.parse_args(prog=prog, args=args, args_parser=parser)
        
        if func.ALLOW_CLEAR_CONSOLE: 
            func.clear_console()

        print_chat_header(prog=prog)
        prog.run()
        
    except (SystemExit, KeyboardInterrupt):
        # Graceful handling for Ctrl+C
        if is_server:
            print(f"\n{Color.YELLOW}[ * ] Neural Hub shutting down...{Color.RESET}")
    except Exception as e:
        if getattr(args, 'debug_console', False):
            traceback.print_exc()
        else:
            func.out(f"{Color.RED}[ ! ] Error: {e}{Color.RESET}") 
        sys.exit(1)
    finally:
        prog.shutdown()
        # Only hard-exit if we aren't trying to keep the server alive
        if not is_server:
            os._exit(0)

if __name__ == "__main__":
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))
    run()