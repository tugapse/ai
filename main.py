from colorama import just_fix_windows_console

just_fix_windows_console()

from dotenv import load_dotenv

load_dotenv()

from time import time
import readline
import argparse
import sys  # Import sys for exiting gracefully

from program import Program
from cli_args import CliArgs
from color import Color
import functions as func


def load_args() -> tuple[argparse.ArgumentParser, argparse.Namespace]:
    """
    Loads command-line arguments for the program.


    Returns:
        argparse.Namespace: The parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(description="AI Assistant")
    parser.add_argument(
        "--msg",
        "-m",
        type=str,
        help="Direct question",
    )
    parser.add_argument(
        "--model", "-md", type=str, help="Model to use"
    )
    parser.add_argument(
        "--system", "-s", type=str, help="pass a prompt name "
    )
    parser.add_argument("--system-file", "-sf", type=str, help="pass a prompt filename")
    parser.add_argument(
        "--list-models",
        "-l",
        action="store_true",
        help="See a list of models available",
    )
    parser.add_argument(
        "--file", "-f", type=str, help="Load a file and pass it as a message"
    )
    parser.add_argument(
        "--image", "-i", type=str, help="Load a image file and pass it as a message"
    )
    parser.add_argument(
        "--load-folder",
        "-D",
        type=str,
        help="Load multiple files from folder and pass them as a message with file location and file content",
    )
    parser.add_argument(
        "--ext", "-e", type=str, help="Provides File extension for folder files search"
    )
    parser.add_argument(
        "--task",
        "-t",
        type=str,
        help="name of the template inside prompt_templates"
    )
    parser.add_argument(
        "--task-file",
        "-tf",
        type=str,
        help="name of the template inside prompt_templates",
    )
    parser.add_argument(
        "--output-file",
        "-o",
        type=str,
        help="filename where the output of automatic actions will be saved",
    )
    parser.add_argument(
        "--auto-task",
        "-at",
        type=str,
        help="filename to a json with auto task configuration",
    )
    parser.add_argument(
        "--print-chat",
        "-p",
        type=str,
        help="filename to a json with with chat log, this can be from ai chats directory or a filename",
    )

    parser.add_argument(
        "--no-log",
        "-q",
        help='Set this flag to NOT print "log" messages',
        action="store_false",
    )
    parser.add_argument(
        "--no-out",
        help='Set this flag to NOT print "output" messages',
        action="store_false",
    )
    parser.add_argument(
        "--debug",
        help='Set this flag to NOT clear console',
        action="store_true",
    )


    return parser, parser.parse_args()


def print_chat_header(prog: Program) -> None:
    """
    Prints initial information about the program.
    Args:
        prog (Program): The program object.
        args (argparse.Namespace): The command-line arguments.
    """

    func.set_console_title("Ai assistant: " + prog.model_chat_name)

    # Ensure prog.config.get('SYSTEM_PROMPT_FILE') returns a string
    system_p_file_path = prog.config.get(
        "SYSTEM_PROMPT_FILE", ""
    )  # Provide a default empty string if key is missing
    system_p_file: str = (
        system_p_file_path.split("/")[-1].replace(".md", "").replace("_", " ")
    )

    # Ensure prog.config.get('SYSTEM_PROMPT_FILE') returns a string
    system_p_file_path = prog.config.get(
        "SYSTEM_PROMPT_FILE", ""
    )  # Provide a default empty string if key is missing
    system_p_file: str = (
        system_p_file_path.split("/")[-1].replace(".md", "").replace("_", " ")
    )
    system_p_file = system_p_file.replace(".md", "").replace("_", " ").capitalize()

    func.out(Color.GREEN, end="")
    func.out(
        f"# Starting {Color.YELLOW}{ prog.model_chat_name }{Color.GREEN} assistant"
    )
    if prog.model_variant:
        func.out(f"# variant {Color.YELLOW}{ prog.model_variant }{Color.GREEN}")
    func.out(f"# Using {Color.YELLOW}{ system_p_file }{Color.GREEN} file system")
    func.out(f"{Color.RESET}--------------------------")


def init_program() -> tuple[Program, argparse.Namespace, argparse.ArgumentParser]:
    """
    Initializes the program components.

    Returns:
        tuple[Program, argparse.Namespace, argparse.ArgumentParser]:
            The program object, parsed arguments, and argument parser.
    """
    prog = Program()
    parser, args = load_args()
    prog.init_program(args)
    return prog, args, parser


if __name__ == "__main__":
    try:
        prog, args, parser = init_program()
        func.log(f"{Color.GREEN} OK", start_line="")
        cli_args_processor = CliArgs()
        cli_args_processor.parse_args(prog=prog, args=args, args_parser=parser)
        if not args.debug: func.clear_console() 
        print_chat_header(prog=prog)
        prog.start_chat_loop()

    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        sys.exit(0)  # Exit the program cleanly

    except Exception as e:
        if args.debug: raise e
        # Catch any other unexpected errors
        func.out(Color.RED + f"\nAn unexpected error occurred: {e}" + Color.RESET)
        sys.exit(1) # Exit with an error code
