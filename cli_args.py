"""
This module provides command-line interface (CLI) arguments parsing and processing.
It allows users to interact with the AI system through various commands and options.
"""

import argparse
import os
import sys
import json

from model_config_manager import ModelConfigManager
from config import ProgramConfig, ProgramSetting
from core.chat import ChatRoles
from core.llms.base_llm import BaseModel
from entities.model_enums import ModelType
from color import Color, format_text
from direct import ask
import functions as func


class CliArgs:
    """
    This class represents the CLI arguments parser.
    It takes care of parsing the user's input, validating it, and executing the corresponding actions.
    """

    def parse_args(self, prog, args, args_parser: argparse.ArgumentParser) -> None:
        """
        Parses the given CLI arguments and executes the corresponding actions.

        :param prog: The program object that will be used to execute the parsed commands.
        :param args: The CLI arguments to be parsed.
        :param args_parser: The main ArgumentParser instance for error reporting.
        """
        # Centralized handling of config generation. This will exit if called.
        self._handle_config_generation(args, args_parser)
        
        # Non-exiting actions
        self._is_print_chat(args)
        self._is_auto_task(args, parser=args_parser)
        self._is_list_models(args)
        self._has_output_files(prog, args)
        self._has_image(prog, args) 
        self._has_folder(prog, args)
        self._has_file(prog, args)
        self._has_task_file(prog, args)
        self._has_task(prog, args)
        self._has_message(prog, args) # This will now trigger `ask` and `sys.exit(0)` if direct input is present


    def _handle_config_generation(self, args, parser: argparse.ArgumentParser):
        """
        Checks for and handles the model configuration generation task.
        If the --generate-config flag is used, it creates the config file and exits.

        :param args: The CLI arguments.
        :param parser: The main ArgumentParser instance for error reporting.
        """
        if args.generate_config:
            if not args.model_name or not args.model_type:
                parser.error(
                    "The --generate-config flag requires both --model-name and --model-type."
                )

            try:
                model_type_enum = ModelType(args.model_type)

                func.log(
                    format_text(
                        f"--- Generating config for {args.model_name} ---", Color.CYAN
                    )
                )

                new_config = ModelConfigManager.generate_default_config(
                    model_name=args.model_name, model_type=model_type_enum
                )

                ModelConfigManager.save_config(new_config, args.generate_config)

                success_message = format_text(
                    f"\nSuccessfully generated and saved configuration to: ",
                    Color.GREEN,
                ) + format_text(f"{args.generate_config}", Color.YELLOW)
                print(success_message)
                print(json.dumps(new_config, indent=2))

            except Exception as e:
                error_msg = format_text(
                    f"An unexpected error occurred during config generation: {e}",
                    Color.RED,
                )
                func.log(f"ERROR: {error_msg}")
                print(error_msg, file=sys.stderr)

            sys.exit(0)

    def _is_print_chat(self, args):
        if args.print_chat:
            from pathlib import Path
            from extras.console import ConsoleChatReader 

            from_logs_file = ((Path(__file__).parent) / "logs" / "chat").joinpath(
                args.print_chat
            )
            from_file = Path(args.print_chat)
            json_filename: str = None

            if from_logs_file.exists():
                json_filename = from_logs_file.resolve()
            elif from_file.exists():
                json_filename = from_file.resolve()
            else:
                raise FileNotFoundError(f"{Color.RED}File not found: {args.print_chat}{Color.RESET}")

            reader = ConsoleChatReader(json_filename)
            reader.load()
            sys.exit(0)

    def _is_auto_task(self, args, parser: argparse):
        if args.auto_task:
            from core.tasks import AutomatedTask

            AutomatedTask(parser).run_task(config_filename=args.auto_task)
            sys.exit(0)

    def _is_list_models(self, args):
        if args.list_models:
            os.system("ollama list")
            sys.exit(0)

    def _has_output_files(self, prog, args):
        if args.output_file:
            prog.write_to_file = True
            prog.output_filename = args.output_file

    def _has_folder(self, prog, args):
        if directory := args.load_folder:
            files = func.get_files(directory, args.ext)
            for file_obj in files:
                file_obj.load()
                # Use BaseModel.create_message for consistency
                prog.chat._add_message(
                    BaseModel.create_message(
                        ChatRoles.USER,
                        f"Filename: {file_obj.filename} \n File Content:\n```{file_obj.content}\n",
                    )
                )
                # Removed the assistant confirmation message, as it's not needed for LLM context
                # prog.chat._add_message(
                #     BaseModel.create_message(
                #         ChatRoles.ASSISTANT,
                #         f"{file_obj.filename} loaded!", 
                #     )
                # )

    def _has_file(self, prog, args):
        if args.file:
            files = args.file.split(",")
            for file_path in files:
                stripped_path = file_path.strip()
                text_content = func.read_file(stripped_path)
                # Use BaseModel.create_message for consistency
                prog.chat._add_message(
                    BaseModel.create_message(
                        ChatRoles.USER,
                        f"Filename: {stripped_path} \n  File Content:\n```{text_content}```",
                    )
                )
                # Removed the assistant confirmation message
                # prog.chat._add_message(
                #     BaseModel.create_message(
                #         ChatRoles.ASSISTANT,
                #         f"{stripped_path} loaded!",
                #     )
                # )

    def _has_image(self, prog, args):
        if args.image:
            files = args.image.split(",")
            for file_path in files:
                stripped_path = file_path.strip()
                if os.path.exists(stripped_path):
                    prog.chat.images.append(stripped_path)
                else:
                    raise FileNotFoundError(f"Image file not found: {stripped_path}")

    def _has_task_file(self, prog, args):
        if args.task_file:
            task_content = func.read_file(args.task_file)
            # Use BaseModel.create_message for consistency
            prog.chat._add_message(BaseModel.create_message(ChatRoles.USER, task_content))

    def _has_task(self, prog, args):
        if args.task:
            task_name = args.task.replace(".md", "") + ".md"
            filepaths_to_check = []
            
            user_tasks_dir = ProgramConfig.current.get(ProgramSetting.PATHS_TASKS_TEMPLATES)
            if user_tasks_dir:
                filepaths_to_check.append(os.path.join(user_tasks_dir, task_name))
            
            global_tasks_dir = ProgramConfig.current.get(ProgramSetting.PATHS_TASKS_TEMPLATES) # Assuming this is a shared path
            if global_tasks_dir and global_tasks_dir != user_tasks_dir: 
                filepaths_to_check.append(os.path.join(global_tasks_dir, task_name))

            found_path = None
            for fp in filepaths_to_check:
                if os.path.exists(fp):
                    found_path = fp
                    break
            
            if not found_path:
                raise FileNotFoundError(f"Task template '{args.task}' not found in configured paths.")

            task_content = func.read_file(found_path)
            # Use BaseModel.create_message for consistency
            prog.chat._add_message(BaseModel.create_message(ChatRoles.USER, task_content))

    def _has_message(self, prog, args):
        piped = False
        if not sys.stdin.isatty():
            piped = True
            prog.chat._add_message( 
                BaseModel.create_message(ChatRoles.USER, sys.stdin.read().strip())
            )
            # Removed the assistant confirmation message "content recieved from pipe!"
            # This was causing the "Chat history ends with an 'assistant' message" warning
            # and is not relevant for the LLM's context.

        if prog.chat.images and len(prog.chat.images):
            message = prog.llm.load_images(prog.chat.images)
            prog.chat.messages.append(message)

        if args.msg:
            prog.chat._add_message( 
                BaseModel.create_message(ChatRoles.USER, args.msg)
            )

        if piped or args.msg or args.task or args.task_file:
            func.log("INFO: Detected message/task input. Starting direct ask.")
            ask(
                prog.llm,
                prog.chat.messages, 
                write_to_file=prog.write_to_file,
                output_filename=prog.output_filename,
            )
            sys.exit(0)
