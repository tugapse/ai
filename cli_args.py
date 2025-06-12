"""
This module provides command-line interface (CLI) arguments parsing and processing.
It allows users to interact with the AI system through various commands and options.
"""

import argparse
import os
import sys

import functions as func
from config import ProgramConfig
from core import ChatRoles, OllamaModel
from color import Color
from direct import ask


class CliArgs:
    """
    This class represents the CLI arguments parser.
    It takes care of parsing the user's input, validating it, and executing the corresponding actions.
    """

    def parse_args(self, prog, args, args_parser) -> None:
        """
        Parses the given CLI arguments and executes the corresponding actions.

        :param prog: The program object that will be used to execute the parsed commands.
        :param args: The CLI arguments to be parsed.
        """
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
        # Check if the user has provided a task file
        self._has_task_file(args)
        # Check if the user has provided a task
        self._has_task(prog, args)
        # Check for message option and add it to the chat's messages
        self._has_message(prog, args)

    def _is_print_chat(self, args):
        if args.print_chat:
            from pathlib import Path
            from_logs_file = ((Path(__file__).parent) /
                              'logs' / 'chat').joinpath(args.print_chat)
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
            files = func.get_files(directory, args.extension)
            messages = list()
            for file in files:
                file.load()
                messages.append(
                    OllamaModel.create_message(
                        ChatRoles.USER,
                        f"Filename: {file.filename} \n File Content:\n```{file.content}\n",
                    )
                )
                prog.chat.messages = messages

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
            args.msg = task

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
            task = func.read_file(filename)
            args.msg = task

    def _has_message(self, prog, args):
        """
        Checks for message option and adds it to the chat's messages.

        :param prog: The program object.
        :param args: The CLI arguments.
        """

        if not sys.stdin.isatty():
            args.msg = sys.stdin.read().strip()

        if args.msg:

            if prog.chat.images and len(prog.chat.images):
                message = prog.llm.load_images(prog.chat.images)
                prog.chat.messages.append(message)

            prog.chat.messages.append(
                OllamaModel.create_message(ChatRoles.USER, args.msg)
            )

            ask(
                prog.llm,
                prog.chat.messages,
                write_to_file=prog.write_to_file,
                output_filename=prog.output_filename,
            )
            exit(0)
