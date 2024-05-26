


from time import time
from typing import Union
import functions as func
from core import OllamaModel,ChatRoles
from extras.console import ConsoleTokenFormatter
from color import Color



def ask(llm:OllamaModel, input_message:Union[str, list[str]],write_to_file=False,output_filename=None) -> None:
    """
    Asks the language model a question.
    
    Args:
        llm (OllamaModel): The language model bot.
        input_message ([str, list[str]]): The user's input message.
        args (argparse.Namespace): The command-line arguments.
    """
    start_time = time()
    first_token_time = None
    end_time = None
    
    if isinstance(input_message, str):
        message = [OllamaModel.create_message(ChatRoles.USER,input_message)]
        # func.out("Prompt has " + str(len(input_message)/4) + " tokens in a " + str(len(input_message)) + " chars string")
    elif isinstance(input_message, list):
        message = input_message
        txt_len = 0
        for line in input_message:
            txt_len = txt_len + len(line['content'] or "")
        # func.out("Prompt has " + str(txt_len / 4) + " tokens in a " +str(txt_len) + " chars string")
    else:
        func.log("Unsupported text type")

    func.log("Loading ֍ ֍ ֍" , end=Color.RESET+"\n")

     # ensure to clean the file
    if write_to_file and output_filename: func.write_to_file(output_filename,"")
    llm_options = {
            'num_ctx': 16384,
            'temperature':0.0,
            'seed':2048
    }

    token_processor = ConsoleTokenFormatter()
    for response in llm.chat(message, stream=True, options=llm_options):
        if first_token_time is None: first_token_time = time()
        new_token = token_processor.process_token(response)
        func.out(new_token, end="",flush=True)
        if write_to_file and output_filename:
            func.write_to_file(output_filename,response,func.FILE_MODE_APPEND)           
    end_time = time()
    func.out("\n")
    func.log(f"{Color.RESET}First token :{Color.YELLOW} {func.format_execution_time(start_time,first_token_time)}")
    func.log(f"{Color.RESET}Time taken  :{Color.YELLOW} {func.format_execution_time(start_time,end_time)}")