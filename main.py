import sys
import os
import argparse
import json
from typing import Optional # FIXED: Added import for Optional

# Add the project root to the sys.path to allow imports from core
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from program import Program
from config import ProgramConfig, ProgramSetting # Now using ProgramSetting as a class of string constants
from entities.model_enums import ModelType
import functions as func
from color import Color
from cli_args import CliArgs # Import the CliArgs processor

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
    
    parser.add_argument("--no-log", "-q", help='Set this flag to NOT print "log" messages', action="store_false")
    parser.add_argument("--no-out", help='Set this flag to NOT print "output" messages', action="store_false")
    
    parser.add_argument("--debug-console","-dc", action="store_true", help='Set this flag to NOT clear console (for debugging)')

    config_group = parser.add_argument_group('Model Config Generation', 'Use these arguments to generate a new model JSON config file.')
    # MODIFIED: Changed help text to reflect that --generate-config now expects a filename
    # which will be saved in the default models directory.
    config_group.add_argument('--generate-config', metavar='FILENAME', type=str, help='Generate a model config and save it to the specified FILENAME in the default models directory, then exit.')
    config_group.add_argument('--model-name', type=str, help="The name of the model to include in the config (e.g., 'meta-llama/Llama-2-7b-chat-hf'). Required by --generate-config.")
    config_group.add_argument('--model-type', type=str, choices=[t.value for t in ModelType], help='The architectural type of the model. Required by --generate-config.')

    return parser, parser.parse_args()


def print_chat_header(prog: Program) -> None:
    """
    Prints initial information about the program.
    """
    func.set_console_title("Ai assistant: " + prog.model_chat_name)

    # MODIFIED: Use ProgramSetting.SYSTEM_PROMPT_FILE for consistency with new config structure
    system_p_file_path = prog.config.get(
        ProgramSetting.SYSTEM_PROMPT_FILE, "" # Use SYSTEM_PROMPT_FILE which holds the resolved path
    )
    system_p_file: str = (
        os.path.basename(system_p_file_path).replace(".md", "").replace("_", " ")
    )
    system_p_file = system_p_file.capitalize()

    func.out(Color.GREEN, end="")
    func.out(
        f"# Starting {Color.YELLOW}{ prog.model_chat_name }{Color.GREEN} assistant"
    )
    if prog.model_variant:
        func.out(f"# variant {Color.YELLOW}{ prog.model_variant }{Color.GREEN}")
    func.out(f"# Using {Color.YELLOW}{ system_p_file }{Color.GREEN} file system")
    func.out(f"{Color.RESET}--------------------------")


def init_program_and_args(args) -> Program: # Changed return type hint
    """
    Initializes the program components and processes CLI arguments.
    """
    
    global clear_console
    
    prog = Program()
    # MODIFIED: ProgramConfig.load() now handles initializing the singleton and its defaults.
    # We pass args to prog.load_config so it can override defaults with CLI arguments.
    prog.load_config(args=args) 
    
    if args.debug_console: 
        print("DEBUG MODE Enabled")
        clear_console = False
        func.LOCK_LOG = False # Directly set LOCK_LOG in functions module
        # MODIFIED: Use ProgramSetting constants for consistency
        prog.config.set(ProgramSetting.PRINT_LOG, True)
        prog.config.set(ProgramSetting.PRINT_DEBUG, True)
    else:
        func.LOCK_LOG = True # Directly set LOCK_LOG in functions module
        # MODIFIED: Use ProgramSetting constants for consistency
        prog.config.set(ProgramSetting.PRINT_LOG, False)
        prog.config.set(ProgramSetting.PRINT_DEBUG, False)

    prog.init_program(args) # Program initialized with args

    return prog


if __name__ == "__main__":
    prog: Optional[Program] = None 
    args: Optional[argparse.Namespace] = None 
    try:
        clear_console = True
        parser, args = load_args()
        
        # Initialize program and parse args
        # The prog object, which holds the ProgramConfig, is returned here
        # and then passed to CliArgs.
        prog = init_program_and_args(args)
        
        # Instantiate CliArgs and parse remaining arguments.
        # _handle_config_generation in CliArgs will exit if --generate-config was used.
        cli_args_processor = CliArgs()
        cli_args_processor.parse_args(prog=prog, args=args, args_parser=parser) # Pass prog object

        if clear_console: 
            func.clear_console()

        print_chat_header(prog=prog)
        
        # Start the chat loop. Direct messages are handled and exit within CliArgs.
        # So, if we reach here, it's for interactive chat.
        prog.start_chat_loop()

    except KeyboardInterrupt:
        print(f"\n{Color.YELLOW}Detected Ctrl+C. Attempting to stop LLM generation gracefully...{Color.RESET}")
        if prog and prog.llm:
            prog.llm.stop_generation_event.set() 
            prog.llm.join_generation_thread(timeout=10)
            if prog.llm._generation_thread and prog.llm._generation_thread.is_alive():
                 print(f"{Color.RED}WARNING: LLM generation thread did not terminate cleanly.{Color.RESET}")
            else:
                 print(f"{Color.GREEN}LLM generation stopped successfully.{Color.RESET}")
        else:
            print(f"{Color.RED}LLM object not initialized or does not support graceful stop.{Color.RESET}")
        sys.exit(0)

    except Exception as e:
        # If an error occurs before args is defined, or if debug_console isn't set,
        # we still want to handle gracefully.
        is_debug_console = False
        if args: # Check if args is not None
            is_debug_console = getattr(args, 'debug_console', False)

        if is_debug_console: 
            raise e
        else:
            print(f"{Color.RED}\nAn unexpected error occurred: {e} {Color.RESET}")
            # Do not re-raise e here, sys.exit(1) is sufficient if not in debug mode.
            sys.exit(1)

