from time import time
from typing import Union
import functions as func
from core import OllamaModel, ChatRoles
from extras.console import ConsoleTokenFormatter
from core.llms.think_parser import ThinkingAnimationHandler
from core.llms.thinking_log_manager import ThinkingLogManager
from core.template_injection import TemplateInjection
from color import Color


class OutputPrinter:
    """
    Manages how LLM output tokens are printed to the console based on the print mode.
    Handles buffering for 'line' and 'every_x_tokens' modes.
    """
    def __init__(self, print_mode: str = "token", tokens_per_print: int = 1):
        self.print_mode = print_mode
        self.tokens_per_print = max(1, tokens_per_print)

        self.line_buffer = ""
        self.token_buffer = ""
        self.buffered_token_count = 0

    def process_and_print(self, token_to_display: str) -> None:
        """
        Processes a single formatted token and prints it based on the configured mode.
        """
        if self.print_mode == "token":
            func.out(token_to_display, end="", flush=True)
        elif self.print_mode == "line":
            self.line_buffer += token_to_display
            if "\n" in self.line_buffer:
                parts = self.line_buffer.split("\n")
                for i in range(len(parts) - 1):
                    func.out(parts[i] + "\n", end="", flush=True)
                self.line_buffer = parts[-1]
        elif self.print_mode == "every_x_tokens":
            self.token_buffer += token_to_display
            self.buffered_token_count += 1
            if self.buffered_token_count >= self.tokens_per_print:
                func.out(self.token_buffer, end="", flush=True)
                self.token_buffer = ""
                self.buffered_token_count = 0
        else:
            func.log(f"Warning: Unknown print_mode '{self.print_mode}'. Defaulting to 'token'.")
            func.out(token_to_display, end="", flush=True)

    def flush_buffers(self) -> None:
        """
        Prints any remaining content in buffers at the end of the stream.
        """
        if self.print_mode == "line" and self.line_buffer:
            func.out(self.line_buffer, end="", flush=True)
            self.line_buffer = ""
        elif self.print_mode == "every_x_tokens" and self.token_buffer:
            func.out(self.token_buffer, end="", flush=True)
            self.token_buffer = ""


def ask(
    llm: OllamaModel,
    input_message: Union[str, list[str]],
    write_to_file=False,
    output_filename=None,
    thinking_mode: str = "spinner",
    print_mode: str = "every_x_tokens",
    tokens_per_print: int = 5,
) -> None:
from typing import Union
import functions as func
from core import OllamaModel,ChatRoles
from extras.console import ConsoleTokenFormatter
from color import Color



def ask(llm:OllamaModel, input_message:Union[str, list[str]],write_to_file=False,output_filename=None) -> None:
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

    thinking_log_manager = ThinkingLogManager(log_file_name="llm_thinking.log")
    # Call write_session_header immediately after initializing the log manager
    thinking_log_manager.write_session_header(tags=llm.model_name)
    injection_template = TemplateInjection(llm.system_prompt)
    llm.system_prompt = injection_template.replace_system_template()


    enable_thinking_display = True
    thinking_handler = ThinkingAnimationHandler(
        enable_display=enable_thinking_display,
        mode=thinking_mode,
        log_manager=thinking_log_manager,
        header_tags=llm.model_name
    )

    output_printer = OutputPrinter(print_mode=print_mode, tokens_per_print=tokens_per_print)

    if isinstance(input_message, str):
        message = [OllamaModel.create_message(ChatRoles.USER, input_message)]
        message = [OllamaModel.create_message(ChatRoles.USER,input_message)]
        # func.out("Prompt has " + str(len(input_message)/4) + " tokens in a " + str(len(input_message)) + " chars string")
    elif isinstance(input_message, list):
        message = input_message
        sum(len(line.get("content", "") or "") for line in input_message)
        txt_len = 0
        for line in input_message:
            txt_len = txt_len + len(line['content'] or "")
        # func.out("Prompt has " + str(txt_len / 4) + " tokens in a " +str(txt_len) + " chars string")
    else:
        func.log("Unsupported input message type for LLM. Expected str or list[dict].")
        return

    func.log("Loading ֍ ֍ ֍", end=Color.RESET + "\n")
        func.log("Unsupported text type")

    if write_to_file and output_filename:
        func.write_to_file(output_filename, "")
    func.log("Loading ֍ ֍ ֍" , end=Color.RESET+"\n")

    llm_options = {
        "num_ctx": llm.CONTEXT_WINDOW_EXTRA_LARGE,
        "temperature": 0.5,
        "seed": llm.CONTEXT_WINDOW_SMALL,
            'num_ctx': llm.CONTEXT_WINDOW_EXTRA_LARGE,
            'temperature':0.5,
            'seed':llm.CONTEXT_WINDOW_SMALL
    }

    token_processor = ConsoleTokenFormatter()
    for raw_token_string in llm.chat(message, stream=True, options=llm_options):
        if first_token_time is None:
            first_token_time = time()
        
        is_thinking, content_after_thinking_handler = thinking_handler.process_token_and_thinking_state(raw_token_string)

        formatted_token_for_display = ""
        if not is_thinking:
            formatted_token_for_display = token_processor.process_token(content_after_thinking_handler)
        
        if not is_thinking and formatted_token_for_display:
            output_printer.process_and_print(formatted_token_for_display)

        if write_to_file and output_filename and formatted_token_for_display:
            func.write_to_file(output_filename, formatted_token_for_display, func.FILE_MODE_APPEND)

    output_printer.flush_buffers()

    for response in llm.chat(message, stream=True, options=llm_options):
        if first_token_time is None: first_token_time = time()
        new_token = token_processor.process_token(response)
        func.out(new_token, end="",flush=True)
        if write_to_file and output_filename:
            func.write_to_file(output_filename,response,func.FILE_MODE_APPEND)           
    end_time = time()
    func.out("\n")

    func.log(
        f"{Color.RESET}First token :{Color.YELLOW} {func.format_execution_time(start_time, first_token_time)}"
    )
    func.log(
        f"{Color.RESET}Time taken  :{Color.YELLOW} {func.format_execution_time(start_time, end_time)}"
    )

    func.out("\n")
    func.log(f"{Color.RESET}First token :{Color.YELLOW} {func.format_execution_time(start_time,first_token_time)}")
    func.log(f"{Color.RESET}Time taken  :{Color.YELLOW} {func.format_execution_time(start_time,end_time)}")