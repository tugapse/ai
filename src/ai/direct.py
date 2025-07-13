import os
from time import time
from typing import Union
import functions as func
from core.llms.base_llm import BaseModel
from core.chat import ChatRoles
from extras.console import ConsoleTokenFormatter
from core.template_injection import TemplateInjection
from color import Color
from extras.output_printer import OutputPrinter
from extras.think_parser import ThinkingAnimationHandler
from extras.thinking_log_manager import ThinkingLogManager
from core.program import ProgramConfig



def ask(
    llm: BaseModel,
    input_message: Union[str, list[str]],
    write_to_file=False,
    output_filename=None,
    thinking_mode: str = "spinner",
    print_mode: str = "line",
    tokens_per_print: int = 5,
) -> None:
    """
    Asks the language model a question and streams its response.

    Args:
        llm (OllamaModel): The language model bot instance.
        input_message (Union[str, list[str]]): The user's input message.
                                               Can be a string or a list of message dictionaries.
        write_to_file (bool): If True, the LLM's output will be written to a file.
        output_filename (str, optional): The filename for output.
        thinking_mode (str): Specifies the visual style of the thinking indicator.
                             Valid options: 'dots', 'spinner', 'progressbar'.
        print_mode (str): Specifies how the LLM's output is printed.
                          Valid options: 'token' (print each token),
                          'line' (print full lines), or
                          'every_x_tokens' (print accumulated tokens after X tokens).
        tokens_per_print (int): The number of tokens to accumulate before printing,
                                used with 'every_x_tokens' print_mode. Must be > 0.
    """
    start_time = time()
    first_token_time = None
    end_time = None


    thinking_log_manager = ThinkingLogManager(log_file_name="active_thinking_process.log")

    injection_template = TemplateInjection(llm.system_prompt)
    llm.system_prompt = injection_template.replace_system_template()

    _config = ProgramConfig.current
    _think_mode = _config.get(ProgramSetting.THINKING_MODE, thinking_mode)
    _print_mode = _config.get(ProgramSetting.PRINT_MODE, print_mode)
    _tokens_per_print = _config.get(ProgramSetting.TOKENS_PER_PRINT, tokens_per_print)
    
    enable_thinking_display = True
    thinking_handler = ThinkingAnimationHandler(
        enable_display=enable_thinking_display,
        mode=_think_mode,
        log_manager=thinking_log_manager
    )

    output_printer = OutputPrinter(print_mode=_print_mode, tokens_per_print=tokens_per_print)

    if isinstance(input_message, str):
        message = [BaseModel.create_message(ChatRoles.USER, input_message)]
    elif isinstance(input_message, list):
        message = input_message
        sum(len(line.get("content", "") or "") for line in input_message)
    else:
        func.log("Unsupported input message type for LLM. Expected str or list[dict].")
        return

    func.log("Loading " + llm.model_name, end=Color.RESET + "\n")

    if write_to_file and output_filename:
        func.write_to_file(output_filename, "")


    token_processor = ConsoleTokenFormatter()
    for raw_token_string in llm.chat(message, stream=True):
        if first_token_time is None:
            first_token_time = time()
        
        is_thinking, content_after_thinking_handler = thinking_handler.process_token_and_thinking_state(raw_token_string)

        
        
        if not is_thinking and content_after_thinking_handler:
            output_printer.process_and_print(content_after_thinking_handler)

        if write_to_file and output_filename and content_after_thinking_handler:
            func.write_to_file(output_filename, content_after_thinking_handler, func.FILE_MODE_APPEND)

    output_printer.flush_buffers()

    end_time = time()
    func.out("\n")

    func.log(
        f"{Color.RESET}First token :{Color.YELLOW} {func.format_execution_time(start_time, first_token_time)}"
    )
    func.log(
        f"{Color.RESET}Time taken  :{Color.YELLOW} {func.format_execution_time(start_time, end_time)}"
    )
