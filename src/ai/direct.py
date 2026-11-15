import os
import re
import unicodedata
from time import time
from typing import Callable, Union, Optional, List, Dict

# Core/Services
import ai.functions as func
from ai.color import Color
from ai.core.llms.base_llm import BaseModel
from ai.tools.tool_registry import ToolRegistry
from ai.chat.chat import ChatRoles
from ai.config import ProgramConfig, ProgramSetting
from ai.services.ui_orchestrator import UIOrchestrator
from ai.extras.think_parser import ThinkingAnimationHandler

def _sanitize_token(token: str) -> str:
    """Cleans and normalizes tokens for clean file output.

    Normalizes Unicode characters and removes control characters (keeping newline
    and tab). Non-ASCII text such as accents, emoji or CJK is preserved.

    Args:
        token: The raw token string from the LLM.

    Returns:
        The sanitized and normalized token string.
    """
    sanitized = unicodedata.normalize('NFKC', token)
    sanitized = re.sub(r'[\x00-\x08\x0b-\x1f\x7f-\x9f]', '', sanitized)
    return sanitized

def ask(
    llm: BaseModel,
    input_message: Union[str, List[Dict[str, str]]],
    write_to_file: bool = False,
    output_filename: Optional[str] = None,
    hide_think_anim: bool = False,
    print_output: bool = True,
    stream: bool = True,
    on_token: Optional[Callable[[str], None]] = None
) -> None:
    """
    Executes a single LLM request (Direct Task).

    This function interfaces with a specified Language Model (LLM) to generate a response.
    It handles streaming output, logging, file writing, and user interface interaction
    based on the provided configuration.

    Args:
        llm: The BaseModel instance representing the LLM to query.
        input_message: The prompt to send to the LLM. Can be a single string or a list of message dictionaries.
        write_to_file: If True, the output will be written to a file.
        output_filename: The path to the file where the output should be saved.
        hide_think_anim: If True, suppresses the thinking animation during processing.
        print_output: If True, prints each token to the console as it is received.
        stream: If True, processes the response token by token instead of waiting for the full response.
        on_token: Optional callback invoked with every sanitized token (including thinking tokens),
            used by interactive UIs to show live progress.
    """
    start_time = time()
    first_token_time = None

    config = ProgramConfig.get_current() or ProgramConfig.load()
    ui = UIOrchestrator(config)
    
    ThinkingAnimationHandler.THINKING_PREFIX = "Processing request"
    ui.initialize(log_filepath="active_thinking_process.log")
    
    ui_tools = ui.get_components()
    printer = ui_tools["printer"]
    handler = ui_tools["handler"]

    if hide_think_anim:
        handler.show_thinking_animation = False

    if isinstance(input_message, str):
        messages = [BaseModel.create_message(ChatRoles.USER, input_message)]
    else:
        messages = input_message

    func.log(f"Direct: Querying {llm.model_name}...")

    if write_to_file and output_filename:
        file_dir = os.path.dirname(os.path.abspath(output_filename))
        if file_dir:
            os.makedirs(file_dir, exist_ok=True)
        func.write_to_file(output_filename, "")

    try:
        output = llm.chat(messages, stream=stream)
        # A whole reply (stream=False) is one token; iterating a str/dict would split it.
        tokens = [output] if isinstance(output, (str, dict)) else output
        for raw_token in tokens:
            if first_token_time is None:
                first_token_time = time()

            # An action dict (the engine caught a tool call) becomes its tool call text.
            token = _sanitize_token(ToolRegistry.as_text(raw_token))
            if not token:
                continue

            if on_token:
                try:
                    on_token(token)
                except Exception as e:
                    func.debug(f"Direct: on_token callback failed: {e}")

            display_to_user, content, _ = handler.process_token_chain(token)

            if display_to_user:
                if print_output:
                    printer.process_and_print(content)

                if write_to_file and output_filename and content:
                    func.write_to_file(
                        output_filename, content, func.FILE_MODE_APPEND
                    )

        printer.flush_buffers()

    except KeyboardInterrupt:
        func.log("\n[!] Task aborted.")
    
    finally:
        end_time = time()
        if print_output:
            func.out("")

        if first_token_time:
            latency = func.format_execution_time(start_time, first_token_time)
            func.log(f"First token latency : {latency}")
        
        total = func.format_execution_time(start_time, end_time)
        func.log(f"Total execution time : {total}")