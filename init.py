from time import time
import readline
import argparse

from ai.core import ChatRoles, LLMBot
from ai.color import Color
from ai import Program, CliArgs, functions as func


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
    parser.add_argument('--load-folder' , '--folder', type=str, help='Load multiple files from folder and pass them as a message with file location and file content')
    parser.add_argument('--extension','--ext', type=str, help='Provides File extension for folder files search')
    parser.add_argument('--task', type=str, help='name of the template inside prompt_templates')
    parser.add_argument('--task-file', type=str, help='name of the template inside prompt_templates')
    parser.add_argument('--output-file', type=str, help='filename where the output of automatic actions will be saved')
    parser.add_argument('--auto-task', type=str, help='filename to a json with auto task configuration')

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

def ask(llm:LLMBot, input_message:[str, list[str]], args=None) -> None:
    """
    Asks the language model a question.
    
    Args:
        llm (LLMBot): The language model bot.
        input_message ([str, list[str]]): The user's input message.
        args (argparse.Namespace): The command-line arguments.
    """
    start_time = time()
    first_token_time = None
    end_time = None
    print_initial_info(prog,args)
    if isinstance(input_message, str):
        message = [LLMBot.create_message(ChatRoles.USER,input_message)]
        print("Prompt has " + str(len(input_message)/4) + " tokens in a " + str(len(input_message)) + " chars string")
    elif isinstance(input_message, list):
        message = input_message
        txt_len = 0
        for line in input_message:
            txt_len = txt_len + len(line['content'] or "")
        print("Prompt has " + str(txt_len / 4) + " tokens in a " +str(txt_len) + " chars string")
    else:
        print("Unsupported text type")

    print("Loading ֍ ֍ ֍")

     # ensure to clean the file
    if prog.write_to_file: func.write_to_file(prog.output_filename,"")
    llm_options = {
            'num_ctx': 16384,
            'temperature':0.0,
            'seed':2048
    }
    
    for response in llm.chat(message, True,options=llm_options):
        if first_token_time is None: first_token_time = time()
        new_token = prog.process_token(response)
        print(new_token, end="",flush=True)
        if prog.write_to_file:
            func.write_to_file(prog.output_filename,response,func.FILE_MODE_APPEND)
    end_time = time()
    print("\n")
    print(f"{Color.RESET}First token :{Color.YELLOW} {func.format_execution_time(start_time,first_token_time)}")
    print(f"{Color.RESET}Time taken  :{Color.YELLOW} {func.format_execution_time(start_time,end_time)}")

def init_program() -> tuple[Program, argparse.Namespace]:
    prog = Program()
    parser, args = load_args()

    prog.init_program(args)
    return prog, args, parser


if __name__ == "__main__":  
    
    prog,args , parser = init_program()
    
    cli_args_processor = CliArgs(prog, ask=ask)
    cli_args_processor.parse_args(prog=prog, args=args, args_parser=parser)
    func.clear_console()
    print_initial_info(prog=prog)
    prog.start_chat_loop()