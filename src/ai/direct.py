import os
import re
import unicodedata
from time import time
from typing import Union, Optional, List, Dict

# Core/Services
import functions as func
from color import Color
from core.llms.base_llm import BaseModel
from core.chat import ChatRoles
from config import ProgramConfig, ProgramSetting
from services.ui_orchestrator import UIOrchestrator
from extras.think_parser import ThinkingAnimationHandler

def _sanitize_token(token: str) -> str:
    """Cleans and normalizes tokens for clean file output."""
    sanitized = unicodedata.normalize('NFKC', token)
    sanitized = re.sub(r'[^\x20-\x7E\n\t]', '', sanitized)
    return sanitized

def ask(
    llm: BaseModel,
    input_message: Union[str, List[Dict[str, str]]],
    write_to_file: bool = False,
    output_filename: Optional[str] = None,
    thinking_mode: str = "spinner",
    print_mode: str = "line",
    tokens_per_print: int = 5,
    hide_think_anim: bool = False,
    print_output: bool = True
) -> None:
    """
    Executes a single LLM request (Direct Task).
    Updated to use existing function constants.
    """
    start_time = time()
    first_token_time = None

    # 1. UI Initialization
    config = ProgramConfig.current or ProgramConfig.load()
    ui = UIOrchestrator(config)
    
    ThinkingAnimationHandler.THINKING_PREFIX = "Processing request"
    ui.initialize(log_filepath="active_thinking_process.log")
    
    ui_tools = ui.get_components()
    printer = ui_tools["printer"]
    handler = ui_tools["handler"]

    if hide_think_anim:
        handler.show_thinking_animation = False

    # 2. Input Prep
    if isinstance(input_message, str):
        messages = [BaseModel.create_message(ChatRoles.USER, input_message)]
    else:
        messages = input_message

    func.log(f"Direct: Querying {llm.model_name}...")

    # 3. File Prep (FIX: Removed non-existent FILE_MODE_WRITE)
    if write_to_file and output_filename:
        file_dir = os.path.dirname(os.path.abspath(output_filename))
        if file_dir:
            os.makedirs(file_dir, exist_ok=True)
        # We call it without a mode to trigger the default 'write/truncate' behavior
        func.write_to_file(output_filename, "")

    # 4. Stream Loop
    try:
        for raw_token in llm.chat(messages, stream=True):
            if first_token_time is None:
                first_token_time = time()

            token = _sanitize_token(raw_token)
            if not token:
                continue

            display_to_user, content, _ = handler.process_token_chain(token)

            if display_to_user:
                if print_output:
                    printer.process_and_print(content)

                if write_to_file and output_filename and content:
                    # Use the constant we know exists
                    func.write_to_file(
                        output_filename, content, func.FILE_MODE_APPEND
                    )

        printer.flush_buffers()

    except KeyboardInterrupt:
        func.log("\n[!] Task aborted.")
    
    finally:
        end_time = time()
        func.out("\n")

        if first_token_time:
            latency = func.format_execution_time(start_time, first_token_time)
            func.log(f"First token latency : {latency}")
        
        total = func.format_execution_time(start_time, end_time)
        func.log(f"Total execution time : {total}")