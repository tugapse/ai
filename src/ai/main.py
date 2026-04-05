import os
import warnings
import logging


def hack_warnings():
    os.environ['TQDM_DISABLE'] = '1'
    os.environ['BITSANDBYTES_NOWELCOME'] = '1'
    os.environ["TRANSFORMERS_VERBOSITY"] = "error"
    logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
    logging.getLogger("huggingface_hub.utils._http").setLevel(logging.ERROR)
    logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
    warnings.filterwarnings("ignore", category=FutureWarning, module="bitsandbytes")
    warnings.filterwarnings("ignore", message=".*local_dir_use_symlinks.*")

hack_warnings()

import sys
import argparse
import importlib.util # Added for dynamic loading
from typing import Optional

from program import Program
from config import ProgramConfig, ProgramSetting
from entities.model_enums import ModelType
import functions as func
from color import Color 
from cli_args import CliArgs 




__version__ = "2.2.0"

# Add the project root to the sys.path to allow imports from core
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

logging.basicConfig(level=logging.ERROR, format='%(name)s - %(levelname)s - %(message)s')

def handle_install(args: argparse.Namespace) -> None:
    """
    Checks for the --install flag and launches the manager.
    Navigates from src/ai/main.py up to project_root/install_engines.py
    """
    if hasattr(args, 'install') and args.install:
        # Step up two levels: src/ai/ -> src/ -> root/
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        installer_path = os.path.join(root, "scripts/install_engines.py")

        if not os.path.exists(installer_path):
            func.out(f"{Color.RED}[ ! ] Installer script not found at: {installer_path}{Color.RESET}")
            sys.exit(1)

        # Dynamically load the installer module from the root
        spec = importlib.util.spec_from_file_location("install_engines", installer_path)
        installer_module = importlib.util.module_from_spec(spec)
        
        try:
            # This executes the script logic (including main_menu)
            spec.loader.exec_module(installer_module)
            # Just in case it doesn't auto-run, we call it explicitly
            if hasattr(installer_module, 'main_menu'):
                installer_module.main_menu()
        except Exception as e:
            func.out(f"{Color.RED}[ ! ] Failed to launch installer: {e}{Color.RESET}")
        
        # Hard exit to prevent main.py from trying to load components
        os._exit(0)

def load_args() -> tuple[argparse.ArgumentParser, argparse.Namespace]:
    # ... (Your existing load_args code remains exactly the same) ...
    parser = argparse.ArgumentParser(description="AI Assistant")
    parser.add_argument("--msg", "-m", type=str, help="Direct question", default=None)
    parser.add_argument("--model", "-md", type=str, help="Model config filename to use")
    parser.add_argument("--system", "-s", type=str, help="pass a prompt name ")
    parser.add_argument("--system-file", "-sf", type=str, help="pass a prompt filename")
    parser.add_argument("--list-models", "-l", action="store_true", help="See a list of models available")
    parser.add_argument("--file", "-f", type=str, help="Load a file")
    parser.add_argument("--image", "-i", type=str, help="Load a image file")
    parser.add_argument("--load-folder", "-D", type=str, help="Load multiple files from folder")
    parser.add_argument("--ext", "-e", type=str, help="File extension for folder search")
    parser.add_argument("--task", "-t", type=str, help="template name")
    parser.add_argument("--task-file", "-tf", type=str, help="template filename")
    parser.add_argument("--output-file", "-o", type=str, help="output filename")
    parser.add_argument("--auto-task", "-at", type=str, help="json auto task config")
    parser.add_argument("--print-chat", "-p", type=str, help="print chat log")
    
    parser.add_argument("--install", help='Install/Update dependencies', action="store_true")
    parser.add_argument("--agent", help='Use agent mode', action="store_true")
    parser.add_argument("--pipeline", "-ppl", type=str, help="Pipeline filename.json")
    
    parser.add_argument("--print-log","-pl", help='print "log" messages', action="store_true")
    parser.add_argument("--print-debug","-pdb", help='print "debug" messages', action="store_true")
    parser.add_argument("--no-out", "-q" ,help='NOT print "output" messages', action="store_true")
    parser.add_argument("--no-think-anim", "-nta" ,help='NOT print "Thinking" animation', action="store_true")
    
    parser.add_argument("--debug-console","-dc", action="store_true", help='NOT clear console')

    config_group = parser.add_argument_group('Model Config Generation')
    config_group.add_argument('--generate-config', metavar='FILENAME', type=str)
    config_group.add_argument('--model-type', type=str, choices=[t.value for t in ModelType])

    return parser, parser.parse_args()


def print_chat_header(prog: Program) -> None:
    # ... (Your existing print_chat_header code remains exactly the same) ...
    func.set_console_title("Ai assistant: " + prog.model_chat_name)
    system_p_file_path = prog.config.get(ProgramSetting.SYSTEM_PROMPT_FILE, "")
    system_p_file: str = os.path.basename(system_p_file_path).replace(".md", "").replace("_", " ")
    system_p_file = system_p_file.capitalize()

    func.out(Color.GREEN, end="")
    func.out(f"# Starting {Color.YELLOW}{ prog.model_chat_name }{Color.GREEN} assistant")
    if prog.model_variant:
        func.out(f"# variant {Color.YELLOW}{ prog.model_variant }{Color.GREEN}")
    func.out(f"# Using {Color.YELLOW}{ system_p_file }{Color.GREEN} file system")
    func.out(f"{Color.RESET}--------------------------")


def init_program_and_args(args) -> Program:
    # ... (Your existing init_program_and_args code remains exactly the same) ...
    global clear_console 
    prog = Program()
    prog.load_config(args=args) 
    
    if args.debug_console: 
        func.log("DEBUG MODE Enabled")
        args.print_log = True
        args.print_debug = True
        func.ALLOW_CLEAR_CONSOLE = False
        func.LOCK_LOG = False 
        prog.config.set(ProgramSetting.PRINT_LOG, True)
        prog.config.set(ProgramSetting.PRINT_DEBUG, True)
    else:
        func.ALLOW_CLEAR_CONSOLE = (not args.print_log and not args.print_debug)

    prog.init_program(args) 
    return prog

def run():
    prog: Optional[Program] = None 
    args: Optional[argparse.Namespace] = None 
    try:
        func.ALLOW_CLEAR_CONSOLE = True
        parser, args = load_args()
        
        handle_install(args)
        
        prog = init_program_and_args(args)
        
        cli_args_processor = CliArgs()
        cli_args_processor.parse_args(prog=prog, args=args, args_parser=parser)

        if func.ALLOW_CLEAR_CONSOLE: 
            func.clear_console()

        print_chat_header(prog=prog)
        prog.run()
        
    except KeyboardInterrupt:
        if prog and prog.llm:
            func.log(f"Detected Ctrl+C. Attempting to stop LLM generation gracefully...") 
            prog.llm.stop_generation_event.set() 
            prog.llm.join_generation_thread(timeout=10)
        os._exit(0)

    except Exception as e:
        is_debug_console = getattr(args, 'debug_console', False) if args else False
        if is_debug_console: 
            raise e
        else:
            func.out(f"An unexpected error occurred: {e}") 
            sys.exit(1)

if __name__ == "__main__":
    run()
    os._exit(0)