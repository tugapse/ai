import os
import sys
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

__version__ = "2.3.2"

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

def run():
    hack_warnings()
    prog: Optional[Program] = None 
    args: Optional[argparse.Namespace] = None 
    
    try:
        # 1. Parse Args
        parser, args = load_args()
        
        # 2. Instantiate and load settings
        prog = Program()
        prog.load_config(args=args) 
        
        # 3. Apply Environment Logic
        if args.debug_console: 
            func.log("DEBUG MODE Enabled")
            func.ALLOW_CLEAR_CONSOLE = False
            func.LOCK_LOG = False 
            prog.config.set(ProgramSetting.PRINT_LOG, True)
            prog.config.set(ProgramSetting.PRINT_DEBUG, True)
        else:
            func.ALLOW_CLEAR_CONSOLE = (not args.print_log and not args.print_debug)
        

        
        # 5. Initialize Hardware and Logic Services
        prog.init_program(args)         
        
        # 4. Process CLI Instructions
        cli_args_processor = CliArgs()
        cli_args_processor.parse_args(prog=prog, args=args, args_parser=parser)
        
   

        # 6. Final UI Prep
        if func.ALLOW_CLEAR_CONSOLE: 
            func.clear_console()

        print_chat_header(prog=prog)
        
        # 7. Start the main loop
        prog.run()
        
    except KeyboardInterrupt:
        os._exit(0)
    except Exception as e:
        # If in debug mode, show full traceback, otherwise show clean error
        is_debug = getattr(args, 'debug_console', False) if args else False
        if is_debug:
            import traceback
            traceback.print_exc()
        else:
            func.out(f"{Color.RED}[ ! ] Error: {e}{Color.RESET}") 
        sys.exit(1)

if __name__ == "__main__":
    # Ensure local module directory is in the sys path
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))
    run()