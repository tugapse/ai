import os
# Set TQDM_DISABLE environment variable to suppress tqdm bars
os.environ['TQDM_DISABLE'] = '1'

import sys
import argparse
import json
from typing import Optional
import logging
from program import Program
from config import ProgramConfig, ProgramSetting
from entities.model_enums import ModelType
import functions as func
from color import Color 
from cli_args import CliArgs # Import the CliArgs processor


__version__ = "2.0.1"

# Add the project root to the sys.path to allow imports from core
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

logging.basicConfig(level=logging.CRITICAL, format='%(name)s - %(levelname)s - %(message)s')


def load_args() -> tuple[argparse.ArgumentParser, argparse.Namespace]:
    """
    Loads command-line arguments for the program.
    """
    parser = argparse.ArgumentParser(description="AI Assistant")

    parser.add_argument("--msg", "-m", type=str, help="Direct question", default=None)
    parser.add_argument("--model", "-md", type=str, help="Model config filename to use (e.g., 'gemma-3-4b-it.json')")
    parser.add_argument("--system", "-s", type=str, help="pass a prompt name ")
    parser.add_argument("--system-file", "-sf", type=str, help="pass a prompt filename")
    parser.add_argument("--list-models", "-l", action="store_true", help="See a list of models available")
    parser.add_argument("--file", "-f", type=str, help="Load a file and pass it as a message")
    parser.add_argument("--image", "-i", type=str, help="Load a image file and pass it as a message")
    parser.add_argument("--load-folder", "-D", type=str, help="Load multiple files from folder and pass them as a message with file location and file content")
    parser.add_argument("--ext", "-e", type=str, help="Provides File extension for folder files search")
    parser.add_argument("--task", "-t", type=str, help="name of the template inside prompt_templates")
    parser.add_argument("--task-file", "-tf", type=str, help="name of the template inside prompt_templates")
    parser.add_argument("--output-file", "-o", type=str, help="filename where the output of automatic actions will be saved")
    parser.add_argument("--auto-task", "-at", type=str, help="filename to a json with auto task configuration")
    parser.add_argument("--print-chat", "-p", type=str, help="filename to a json with with chat log, this can be from ai chats directory or a filename")
    
    parser.add_argument("--print-log", help='Set this flag to print "log" messages', action="store_true")
    parser.add_argument("--print-debug", help='Set this flag to print "debug" messages', action="store_true")
    parser.add_argument("--no-out", "-q" ,help='Set this flag to NOT print "output" messages', action="store_false")
    
    parser.add_argument("--debug-console","-dc", action="store_true", help='Set this flag to NOT clear console (for debugging)')

    config_group = parser.add_argument_group('Model Config Generation', 'Use these arguments to generate a new model JSON config file.')
    config_group.add_argument('--generate-config', metavar='FILENAME', type=str, help='Generate a model config and save it to the specified FILENAME in the default models directory, then exit.')
    config_group.add_argument('--model-name', type=str, help="The name of the model to include in the config (e.g., 'meta-llama/Llama-2-7b-chat-hf'). Required by --generate-config.")
    config_group.add_argument('--model-type', type=str, choices=[t.value for t in ModelType], help='The architectural type of the model. Required by --generate-config.')

    return parser, parser.parse_args()


def print_chat_header(prog: Program) -> None:
    """
    Prints initial information about the program.
    """
    func.set_console_title("Ai assistant: " + prog.model_chat_name)

    system_p_file_path = prog.config.get(
        ProgramSetting.SYSTEM_PROMPT_FILE, ""
    )
    system_p_file: str = (
        os.path.basename(system_p_file_path).replace(".md", "").replace("_", " ")
    )
    system_p_file = system_p_file.capitalize()

    func.out(Color.GREEN, end="") # Reverted to func.out
    func.out( # Reverted to func.out
        f"# Starting {Color.YELLOW}{ prog.model_chat_name }{Color.GREEN} assistant"
    )
    if prog.model_variant:
        func.out(f"# variant {Color.YELLOW}{ prog.model_variant }{Color.GREEN}") # Reverted to func.out
    func.out(f"# Using {Color.YELLOW}{ system_p_file }{Color.GREEN} file system") # Reverted to func.out
    func.out(f"{Color.RESET}--------------------------") # Reverted to func.out


def init_program_and_args(args) -> Program:
    """
    Initializes the program components and processes CLI arguments.
    """
    
    global clear_console 
    
    prog = Program()
    prog.load_config(args=args) 
    
    if args.debug_console: 
        func.log("DEBUG MODE Enabled") # Reverted to func.log
        args.print_log = True
        args.print_debug = True
        clear_console = False
        func.LOCK_LOG = False 
        prog.config.set(ProgramSetting.PRINT_LOG, True)
        prog.config.set(ProgramSetting.PRINT_DEBUG, True)

    prog.init_program(args) 

    return prog

def run():
    prog: Optional[Program] = None 
    args: Optional[argparse.Namespace] = None 
    try:
        func.CLEAR_CONSOLE = True
        parser, args = load_args()
        
        prog = init_program_and_args(args)
        
        cli_args_processor = CliArgs()
        cli_args_processor.parse_args(prog=prog, args=args, args_parser=parser)

        if func.CLEAR_CONSOLE: 
            func.clear_console()

        print_chat_header(prog=prog)
        prog.start_chat_loop()
    except KeyboardInterrupt:
        func.log(f"Detected Ctrl+C. Attempting to stop LLM generation gracefully...", level="WARNING") 
        if prog and prog.llm:
            prog.llm.stop_generation_event.set() 
            prog.llm.join_generation_thread(timeout=10)
            if prog.llm._generation_thread and prog.llm._generation_thread.is_alive():
                 func.log(f"LLM generation thread did not terminate cleanly.", level="WARNING") 
            else:
                 func.log(f"LLM generation stopped successfully.") 
        else:
            func.log(f"LLM object not initialized or does not support graceful stop.", level="ERROR") 
        sys.exit(0)

    except Exception as e:
        is_debug_console = False
        if args: 
            is_debug_console = getattr(args, 'debug_console', False)

        if is_debug_console: 
            raise e
        else:
            func.out(f"An unexpected error occurred: {e}", level="ERROR") 
            sys.exit(1)

if __name__ == "__main__":
    run()

