from colorama import just_fix_windows_console
just_fix_windows_console()

from dotenv import load_dotenv
load_dotenv()

from time import time
import readline
import argparse

from program import Program
from cli_args import CliArgs
from setup import Setup
from color import Color
import functions as func


def load_args() -> tuple[argparse.ArgumentParser, argparse.Namespace]:
    """
    Loads command-line arguments for the program.
    
    Returns:
        argparse.Namespace: The parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(description='AI Assistant')
    parser.add_argument('--msg', type=str, help='Direct question')
    parser.add_argument('--model', type=str, help='Model to use')
    parser.add_argument('--system', type=str, help='pass a prompt name ')
    parser.add_argument('--system-file', type=str, help='pass a prompt filename')
    parser.add_argument('--list-models', action="store_true", help='See a list of models available')
    parser.add_argument('--file' , '--files', type=str, help='Load a file and pass it as a message')
    parser.add_argument('--image' , '--images', type=str, help='Load a image or images')
    parser.add_argument('--load-folder' , '--folder', type=str, help='Load multiple files from folder and pass them as a message with file location and file content')
    parser.add_argument('--extension','--ext', type=str, help='Provides File extension for folder files search')
    parser.add_argument('--task', type=str, help='name of the template inside prompt_templates')
    parser.add_argument('--task-file', type=str, help='name of the template inside prompt_templates')
    parser.add_argument('--output-file', type=str, help='filename where the output of automatic actions will be saved')
    parser.add_argument('--auto-task', type=str, help='filename to a json with auto task configuration')
    parser.add_argument('--print-chat', type=str, help='filename to a json with with chat log, this can be from ai chats directory or a filename')

    return parser, parser.parse_args()

def print_initial_info(prog:Program) -> None:
    """
    Prints initial information about the program.
    
    Args:
        prog (Program): The program object.
        args (argparse.Namespace): The command-line arguments.
    """
   
    func.set_console_title("Ai assistant: " + prog.model_chat_name)
    
    system_p_file :str = prog.config.get('SYSTEM_PROMPT_FILE').split("/")[-1].replace('.md','').replace('_'," ")
    system_p_file = system_p_file.replace('.md','').replace('_'," ").capitalize()
    
    print(Color.GREEN,end="")
    print(f"# Starting {Color.YELLOW}{ prog.model_chat_name }{Color.GREEN} assistant")
    if prog.model_variant : print(f"# variant {Color.YELLOW}{ prog.model_variant }{Color.GREEN}") 
    print(f"# Using {Color.YELLOW}{ system_p_file }{Color.GREEN} file system")
    print(f"{Color.RESET}--------------------------")



def init_program() -> tuple[Program, argparse.Namespace]:
    prog = Program()
    parser, args = load_args()

    prog.init_program(args)
    return prog, args, parser


if __name__ == "__main__":  
    
    prog,args , parser = init_program()
    
    print(f"{Color.YELLOW}Checking system :")
    Setup().perform_check()
    print(f"{Color.GREEN}# System pass")
    
    cli_args_processor = CliArgs()
    cli_args_processor.parse_args(prog=prog, args=args, args_parser=parser)
    func.clear_console()
    print_initial_info(prog=prog)
    prog.start_chat_loop()