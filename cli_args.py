"""
This module provides command-line interface (CLI) arguments parsing and processing.
It allows users to interact with the AI system through various commands and options.
"""

import argparse
import os
import sys


from model_config_manager import ModelConfigManager
from config import ProgramConfig
from core.chat import ChatRoles
from core.llms.base_llm import BaseModel
from core.llms.model_enums import ModelType
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
        # --- Handle config generation first, and exit if called ---
        self._handle_config_generation(args, args_parser)
        # --------------------------------------------------------

        self._is_print_chat(args)
        # check for automatic tasks
        self._is_auto_task(args, parser=args_parser)
        # Check if the user wants to list all available models
        self._is_list_models(args)
        # Check if the user wants to load a single file
        self._has_image(prog, args)
        # Check if the user wants to load a single file
        self._has_file(prog, args)
        # Check if the user wants to load images
        self._has_image(prog, args)
        # Check if the user wants to load a folder with files
        self._has_folder(prog, args)
        # Check for output file option and set the corresponding flag in the program
        self._has_output_files(prog, args)
        # Check for message option and add it to the chat's messages
        self._has_message(prog, args)
        self._has_output_files(prog, args)
        # Check for message option and add it to the chat's messages
        self._has_message(prog, args)
        # Check if the user has provided a task file
        self._has_task_file(args)
        # Check if the user has provided a task
        self._has_task(prog, args)

    def _handle_config_generation(self, args, parser: argparse.ArgumentParser):
        """
        Checks for and handles the model configuration generation task.
        If the --generate-config flag is used, it creates the config file and exits.

        :param args: The CLI arguments.
        :param parser: The main ArgumentParser instance for error reporting.
        """
        if args.generate_config:
            # Check if required arguments for this action are provided
            if not args.model_name or not args.model_type:
                parser.error(
                    "The --generate-config flag requires both --model-name and --model-type."
                )

            try:
                # Convert model_type string to Enum
                model_type_enum = ModelType(args.model_type)

                # Generate and save the configuration
                func.log(
                    format_text(
                        f"--- Generating config for {args.model_name} ---", Color.CYAN
                    )
                )

                new_config = ModelConfigManager.generate_default_config(
                    model_name=args.model_name, model_type=model_type_enum
                )

                ModelConfigManager.save_config(new_config, args.generate_config)

                # Print success message and exit
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

            # Exit the program since the task is complete
            sys.exit(0)

    def _is_print_chat(self, args):
        if args.print_chat:
            from pathlib import Path

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
                raise FileNotFoundError(f"{Color.RED}", args.print_chat)

            from extras.console import ConsoleChatReader

            reader = ConsoleChatReader(json_filename)
            reader.load()
            exit()

    def _is_auto_task(self, args, parser: argparse):
        if args.auto_task:
            from core.tasks import AutomatedTask

            AutomatedTask(parser).run_task(config_filename=args.auto_task)
            exit(0)

    def _is_list_models(self, args):
        """
        Checks if the user wants to list all available models.

        :param args: The CLI arguments.
        """

        if args.list_models:
            os.system("ollama list")
            exit(0)

    def _has_output_files(self, prog, args):
        """
        Checks for output file option and sets the corresponding flag in the program.

        :param prog: The program object.
        :param args: The CLI arguments.
        """

        if args.output_file:
            prog.write_to_file = True
            prog.output_filename = args.output_file

    def _has_folder(self, prog, args):
        """
        Checks if the user wants to load a folder with files.

        :param prog: The program object.
        :param args: The CLI arguments.
        """

        if directory := args.load_folder:
            files = func.get_files(directory, args.ext)
            messages = list()
            for file in files:
                file.load()
                messages.append(
                    BaseModel.create_message(
                        ChatRoles.USER,
                        f"Filename: {file.filename} \n File Content:\n```{file.content}\n",
                    )
                )
                messages.append(
                    BaseModel.create_message(
                        ChatRoles.ASSISTANT,
                        f"{args.file} loaded!",
                    )
                )
                prog.chat.messages = messages

    def _has_file(self, prog, args):
        """
        Checks if the user wants to load a single file.

        :param prog: The program object.
        :param args: The CLI arguments.
        """

        if args.file:
            files = args.file.split(",")
            for file in files:
                text_file = func.read_file(file.strip())
                prog.chat._add_message(
                    ChatRoles.USER,
                    f"Filename: {args.file} \n  File Content:\n```{text_file}```",
                )
                prog.chat._add_message(
                    ChatRoles.ASSISTANT,
                    f"{args.file} loaded!",
                )

    def _has_image(self, prog, args):
        """
        Checks if the user wants to load image or images.

        :param prog: The program object.
        :param args: The CLI arguments.
        """

        if args.image:
            files = args.image.split(",")
            for file in files:
                if os.path.exists(file):
                    prog.chat.images.append(file)
                else:
                    raise FileNotFoundError(file)

    def _has_task_file(self, args):
        """
        Checks if the user has provided a task file.

        :param args: The CLI arguments.
        """

        if args.task_file:
            task = func.read_file(args.task_file)
            prog.chat.messages.append(BaseModel.create_message(ChatRoles.USER, task))

    def _has_task(self, prog, args):
        """
        Checks if the user has provided a task.

        :param prog: The program object.
        :param args: The CLI arguments.
        """

        if args.task:
            filename = os.path.join(
                ProgramConfig.current.config["USER_PATHS"]["TASKS_TEMPLATES"],
                args.task.replace(".md", "") + ".md",
            )
            if not os.path.exists(filename):
                filename = os.path.join(
                    ProgramConfig.current.config["PATHS"]["TASKS_TEMPLATES"],
                    args.task.replace(".md", "") + ".md",
                )
            filename = os.path.join(
                ProgramConfig.current.config[ProgramSetting.USER_PATHS][
                    ProgramSetting.TASKS_TEMPLATES
                ],
                args.task.replace(".md", "") + ".md",
            )
            if not os.path.exists(filename):
                filename = os.path.join(
                    ProgramConfig.current.config[ProgramSetting.PATHS][
                        ProgramSetting.TASKS_TEMPLATES
                    ],
                    args.task.replace(".md", "") + ".md",
                )
            task = func.read_file(filename)
            prog.chat.messages.append(BaseModel.create_message(ChatRoles.USER, task))

    def _has_message(self, prog, args):
        """
        Checks for message option and adds it to the chat's messages.

        :param prog: The program object.
        :param args: The CLI arguments.
        """
        piped = False
        if not sys.stdin.isatty():
            piped = True
            prog.chat.messages.append(
                BaseModel.create_message(ChatRoles.USER, sys.stdin.read().strip())
            )
            prog.chat.messages.append(
                BaseModel.create_message(
                    ChatRoles.ASSISTANT, "content recieved from pipe!"
                )
            )

        if prog.chat.images and len(prog.chat.images):
            message = prog.llm.load_images(prog.chat.images)
            prog.chat.messages.append(message)

        if args.msg:
            prog.chat.messages.append(
                BaseModel.create_message(ChatRoles.USER, args.msg)
            )
            # prog.chat.messages.append(
            #     BaseModel.create_message(ChatRoles.CONTROL, "thinking")
            # )

        if piped or args.msg or args.task:
            ask(
                prog.llm,
                prog.chat.messages,
                write_to_file=prog.write_to_file,
                output_filename=prog.output_filename,
            )
            exit(0)
