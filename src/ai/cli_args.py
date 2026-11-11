"""
This module provides command-line interface (CLI) arguments parsing and processing.
It coordinates the JARVIS behavior mode: Standalone, Server, or Client.
"""

import argparse
import os
import sys
import subprocess
from pathlib import Path

import uuid
import traceback
import re
from typing import Optional

# Configuration and Enums
from ai.agents.session_manager import AgentSessionManager
from ai.modules.server.brain_hub import BrainHub
from ai.model_config_manager import ModelConfigManager
from ai.config import ProgramConfig, ProgramSetting 
from ai.entities.model_enums import ModelType

# Core logic
from ai.chat.chat import ChatRoles
from ai.core.llms.base_llm import BaseModel
from ai.color import Color, format_text
from ai.direct import ask

# Agent logic
from ai.agents.agent import AgentOrchestrator, LLMConnector, ToolRegistry, load_pipeline_config, build_orchestrator
from ai.program import Program
from ai.services.directory_manager import DirectoryManager
from ai.tools.tool_loader import load_and_register_user_tools
import ai.tools.agent_tools as agent_tools

import ai.functions as func

class CliArgs:
    """
    Main orchestrator for CLI input. Handles mode dispatching 
    and ensures proper initialization based on the user's intent.
    """

    def parse_args(self, prog, args, args_parser: argparse.ArgumentParser, directory_manager: DirectoryManager) -> None:
        """
        The main dispatcher. Analyzes arguments to decide if JARVIS 
        acts as a Brain (Server), a Body (Client), or a Standalone agent.

        :param prog: The main program instance.
        :param args: The parsed command-line arguments.
        :param args_parser: The argument parser object.
        :param directory_manager: The directory management service.
        :raises SystemExit: Exits the program upon successful execution of a specific CLI command.
        """
        # 1. System/Global Actions
        self._check_nhandle_create_tool(args, directory_manager)
        self._check_nhandle_config_generation(prog, args, args_parser, directory_manager) 
        self._is_install(args)
        self._is_print_chat(args)
        self._is_list_models(args)
        self._check_nhandle_list_sessions(args)

        # 2. Mode Dispatching
        # Check for Server Mode (Main PC)
        if hasattr(args, 'server') and args.server:
            self._handle_server_mode(prog, args)
            os._exit(0)

        # Default to Local/Direct Task Mode
        self._handle_local_direct_mode(prog, args,directory_manager=directory_manager)

        # 3. Execution Dispatching
        if args.agent:
            self._handle_agent_mode(prog, args, directory_manager)
            os._exit(0) 

        self._has_message(prog, args) 
    
    def _check_nhandle_create_tool(self, args, directory_manager: DirectoryManager):
        """
        Handles the creation of a new tool skeleton file based on the provided name.

        :param args: The parsed command-line arguments containing the tool name.
        :param directory_manager: The service responsible for managing file paths.
        :raises SystemExit: Exits if the tool name is invalid or the file already exists.
        """
        if not args.create_tool:
            return

        tool_name = args.create_tool
        
        base_name = tool_name.strip().replace(' ', '_').replace('-', '_')
        base_name = re.sub(r'[^a-zA-Z0-9_]', '', base_name)
        if base_name and base_name[0].isdigit():
            base_name = '_' + base_name

        if not base_name:
            func.error("Invalid tool name. Please use alphanumeric characters, spaces, or hyphens.")
            sys.exit(1)

        filename = f"{base_name}.py"
        function_name = base_name

        user_tools_dir = directory_manager.get_user_tools_directory()
        func.ensure_directory_exists(user_tools_dir)

        file_path = os.path.join(user_tools_dir, filename)

        if os.path.exists(file_path):
            func.error(f"Tool file already exists: {file_path}")
            sys.exit(1)

        # Using double braces {{ }} for literal braces in the generated code
        skeleton_content = f"""
from ai.tools.agent_tools import tool

@tool
def {function_name}(argument: str) -> str:
    \"\"\"A brief description of what this tool does.

    Args:
        argument (str): A description of the argument.

    Returns:
        str: A description of the return value.
    \"\"\"
    try:
        
        result = f"Executing {function_name} with: {{argument}}"

        return {{"status": "SUCCESS", "result": result}}
    except Exception as e:
        return {{"status": "FAILED", "error": str(e)}}
"""
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(skeleton_content.strip())
            
            func.out(f"{Color.GREEN}[+] Tool skeleton created successfully at: {file_path}{Color.RESET}")

        except Exception as e:
            func.error(f"Failed to create tool file: {e}")
            sys.exit(1)
        
        sys.exit(0)


    def _handle_server_mode(self, prog:Program, args):
        """
        Initializes and starts the JARVIS server mode.

        :param prog: The main program instance containing configuration and models.
        :param args: The parsed arguments, which must contain the --server flag.
        :raises KeyboardInterrupt: Catches Ctrl+C to gracefully shut down the server.
        """
        if args.server:
            try:
                orchestrator = prog.models 
                if args.model:
                    try:
                        orchestrator.load(args.model,"")
                    except Exception as e:
                        func.log(f"{Color.RED}[ ! ] Neural Load Failed: {e}. Starting in STANDBY.{Color.RESET}")
                else:
                    func.log(f"{Color.CYAN}[*] Neural Hub: Standby Mode. Awaiting Neural Link...{Color.RESET}")
                
                from ai.modules.server.server_module import JarvisServerModule
                server = JarvisServerModule( 
                    host=prog.config.get(ProgramSetting.SERVER_HOST, "0.0.0.0"),
                    port=prog.config.get(ProgramSetting.SERVER_PORT, 9999),
                    brain_hub=BrainHub(prog.config) 
                )
                
                server.initialize(prog.config, orchestrator, prog.history)
                server.start()
                
            except KeyboardInterrupt:
                func.log(f"\n{Color.YELLOW}[ * ] Manual override engaged. Terminating JARVIS server.{Color.RESET}")
                sys.exit(0)
                
    def _handle_local_direct_mode(self, prog, args,directory_manager:DirectoryManager):
        """
        The standard non-agent loop for one-shot tasks and context loading.
        Checks for various input sources (files, images, tasks) before proceeding to ask.

        :param prog: The main program instance.
        :param args: The parsed command-line arguments.
        :param directory_manager: The directory management service.
        """
        self._has_output_files(prog, args)
        self._has_image(prog, args) 
        self._has_folder(prog, args)
        self._has_file(prog, args)
        self._has_task_file(prog, args)
        self._has_task(prog, args)
        

    def _handle_agent_mode(self, prog:Program, args, directory_manager: DirectoryManager):
        """
        Handles the execution of the agent pipeline using a specified or default pipeline configuration.

        :param prog: The main program instance.
        :param args: The parsed command-line arguments, including task/message input.
        :param directory_manager: The directory management service for loading user tools.
        :raises SystemExit: Exits after the agent loop completes or fails.
        """
        taskfile = ""
        _task = ""
        if args.task_file:
             taskfile = func.read_file(args.task_file)
        
        if args.task:
            task_name = f"{args.task.replace('.md', '')}.md"
            user_tasks_dir = os.path.join( directory_manager.get_user_directory(), "task")
            found_path = os.path.join(user_tasks_dir, task_name)
            
            if not os.path.exists(found_path):
                raise FileNotFoundError(f"Task template '{args.task}' not found.")
            _task = func.read_file(found_path)

        user_input = taskfile or _task 
        if not sys.stdin.isatty():
            piped_input = sys.stdin.read().strip()
            if piped_input:
                if user_input : user_input += "\n" + piped_input
                else:  user_input = piped_input
        user_input = user_input + args.msg if args.msg else user_input

        pipeline_path = args.pipeline or "default.json"

        if not user_input:
            # Interactive terminal and no prompt: open the agent chat.
            if sys.stdin.isatty() and sys.stdout.isatty() and not args.output_file:
                self._handle_agent_chat(prog, args, directory_manager, pipeline_path)
                sys.exit(0)
            func.error("Agent mode requires a prompt. Use --msg, --task, or pipe input.")
            sys.exit(1)

        try:
            orchestrator = build_orchestrator(prog, pipeline_path, directory_manager=directory_manager)
        except ValueError as e:
            func.error(f"{e} Aborting.")
            sys.exit(1)

        session_id = args.session_id or str(uuid.uuid4())
        func.log(f"Session: {session_id}")

        try:
            orchestrator.run_loop(user_prompt=user_input, session_id=session_id)
        except Exception as e:
            func.error(f"Orchestrator Error: {e}")
            func.error(traceback.format_exc())
        finally:
            sys.exit(0)

    def _handle_agent_chat(self, prog: Program, args, directory_manager: DirectoryManager, pipeline_path: str):
        """
        Starts the interactive multi-turn agent chat (prompt_toolkit UI).

        :param prog: The main program instance.
        :param args: The parsed command-line arguments (uses --session-id).
        :param directory_manager: The directory management service.
        :param pipeline_path: The pipeline configuration to load.
        """
        from ai.agents.chat_ui.app import run_agent_chat

        try:
            run_agent_chat(
                prog,
                pipeline=pipeline_path,
                session_id=args.session_id,
                directory_manager=directory_manager,
            )
        except ValueError as e:
            func.error(f"{e} Aborting.")
            sys.exit(1)
        except Exception as e:
            func.error(f"Agent chat error: {e}")
            func.error(traceback.format_exc())
            sys.exit(1)

    def _check_nhandle_config_generation(self, prog, args, parser: argparse.ArgumentParser, directory_manager: DirectoryManager):
        """
        Generates a default model configuration file based on user input.

        :param prog: The main program instance.
        :param args: The parsed arguments containing configuration generation flags.
        :param parser: The argument parser instance, used for error reporting.
        :param directory_manager: The directory management service.
        :raises SystemExit: Exits after successfully generating the config or upon failure.
        """
        if not args.generate_config:
            return

        if not args.model_type:
            parser.error("The --generate-config flag requires --model-type.")

        try:
            model_type_enum = ModelType(args.model_type)
            config_filename = args.generate_config if args.generate_config.endswith(".json") else f"{args.generate_config}.json"
            
            models_dir = directory_manager.get_system_models_directory()
            func.ensure_directory_exists(models_dir)

            full_filepath = os.path.join(models_dir, config_filename)
            new_config = ModelConfigManager.generate_default_config(model_name=args.generate_config, model_type=model_type_enum)

            ModelConfigManager.save_config(new_config, full_filepath) 
            print(format_text(f"\nConfiguration saved to: {full_filepath}", Color.GREEN))
        except Exception as e:
            func.error(f"Config generation failed: {e}")
        sys.exit(0)

    def _is_print_chat(self, args):
        """
        Prints the content of a specified chat log file to the console.

        :param args: The parsed arguments containing the chat file path.
        :raises SystemExit: Exits after printing the chat or if the file is not found.
        """
        if not args.print_chat:
            return
        from pathlib import Path
        from ai.extras.console import ConsoleChatReader
        
        # Logic to find the file in logs or local path
        log_path = (Path(__file__).parent / "logs" / "chat") / args.print_chat
        local_path = Path(args.print_chat)
        
        target = log_path if log_path.exists() else local_path if local_path.exists() else None
        
        if not target:
            func.error(f"Chat file not found: {args.print_chat}")
            sys.exit(1)

        reader = ConsoleChatReader(str(target.resolve()))
        reader.load()
        sys.exit(0)

    def _is_install(self, args):
        """
        Handles the installation or updating of necessary engine components.

        :param args: The parsed arguments containing the --install flag.
        :raises FileNotFoundError: If required installer or virtual environment files are missing.
        :raises ImportError: If the installer module cannot be loaded.
        :raises SystemExit: Exits after installation is complete or if an error occurs.
        """
        if args.install:
            import importlib.util
            if getattr(sys, "frozen", False):
                project_root = Path(sys.executable).resolve().parent.parent
            else:
                project_root = Path(__file__).resolve().parent.parent.parent

            installer_path = project_root / "scripts" / "install_engines.py"
            if not installer_path.is_file():
                raise FileNotFoundError(
                    f"Engine installer not found at '{installer_path}'. "
                    "Run --install from the project checkout."
                )

            if getattr(sys, "frozen", False):
                venv_python = project_root / ".venv" / "Scripts" / "python.exe"
                if not venv_python.is_file():
                    raise FileNotFoundError(
                        f"Project virtual environment not found at '{venv_python}'. "
                        "Run .\\build.ps1 from the project checkout first."
                    )
                subprocess.run(
                    [str(venv_python), str(installer_path)],
                    cwd=project_root,
                    check=True,
                )
                func.out(
                    "Engine installation updated the project environment. "
                    "Run .\\compile.ps1 to include changes in the executable."
                )
                sys.exit(0)

            spec = importlib.util.spec_from_file_location("install_engines", installer_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not load engine installer from '{installer_path}'.")

            installer_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(installer_module)
            installer_module.main_menu()
            sys.exit(0)

    def _is_list_models(self, args):
        """
        Lists available models. Currently provides a placeholder message.

        :param args: The parsed arguments containing the --list-models flag.
        :raises SystemExit: Exits after displaying the status message.
        """
        if args.list_models:
            # FIXME read the user dir and list all models
            func.out("Not available at the moment: ", level="WARN")
            sys.exit(0)

    def _has_output_files(self, prog, args):
        """
        Checks for output file arguments and sets the program's output configuration.

        :param prog: The main program instance.
        :param args: The parsed command-line arguments.
        """
        if args.output_file:
            prog.write_to_file = True
            prog.output_filename = args.output_file

    def _has_folder(self, prog, args):
        """
        Loads content from a specified directory into the chat context.

        :param prog: The main program instance.
        :param args: The parsed command-line arguments containing the directory path and extension.
        """
        if directory := args.load_folder:
            files = func.get_files(directory, args.ext)
            for file_obj in files:
                file_obj.load()
                prog.chat._add_message(BaseModel.create_message(ChatRoles.USER, f"Filename: {file_obj.filename} \nContent:\n```{file_obj.content}\n"))

    def _has_file(self, prog, args):
        """
        Loads content from one or more specified files into the chat context.

        :param prog: The main program instance.
        :param args: The parsed command-line arguments containing comma-separated file paths.
        """
        if args.file:
            for file_path in args.file.split(","):
                text_content = func.read_file(file_path.strip())
                prog.chat._add_message(BaseModel.create_message(ChatRoles.USER, f"Filename: {file_path.strip()} \nContent:\n```{text_content}```"))

    def _has_image(self, prog, args):
        """
        Adds image file paths to the chat context for multimodal processing.

        :param prog: The main program instance.
        :param args: The parsed command-line arguments containing comma-separated image paths.
        :raises FileNotFoundError: If any specified image path does not exist.
        """
        if args.image:
            for file_path in args.image.split(","):
                path = file_path.strip()
                if os.path.exists(path):
                    prog.chat.images.append(path)
                else:
                    raise FileNotFoundError(f"Image not found: {path}")

    def _has_task_file(self, prog, args):
        """
        Loads the content of a specific task file into the chat context.

        :param prog: The main program instance.
        :param args: The parsed command-line arguments containing the task file path.
        """
        if args.task_file:
            prog.chat._add_message(BaseModel.create_message(ChatRoles.USER, func.read_file(args.task_file)))

    def _has_task(self, prog, args):
        """
        Loads a predefined task template from the configured tasks directory into the chat context.

        :param prog: The main program instance.
        :param args: The parsed command-line arguments containing the task name (e.g., 'summary').
        :raises FileNotFoundError: If the specified task template file does not exist.
        """
        if args.task:
            task_name = f"{args.task.replace('.md', '')}.md"
            user_tasks_dir = os.path.join( DirectoryManager().get_user_directory(), "task")
            found_path = os.path.join(user_tasks_dir, task_name)
            
            if not os.path.exists(found_path):
                raise FileNotFoundError(f"Task template '{args.task}' not found.")

            prog.chat._add_message(BaseModel.create_message(ChatRoles.USER, func.read_file(found_path)))
            
    def _has_message(self, prog, args):
        """
        Handles the final user message input, including piped stdin, and initiates the direct ask process.

        :param prog: The main program instance.
        :param args: The parsed command-line arguments.
        :raises SystemExit: Exits after calling the ask function.
        """
        has_piped_input = False
        piped_input = ""
        
        if not sys.stdin.isatty():
            piped_input = sys.stdin.read().strip()
            if piped_input:
                has_piped_input = True
                prog.chat._add_message(BaseModel.create_message(ChatRoles.USER, piped_input))

        if prog.chat.images:
            message = prog.llm.load_images(prog.chat.images)
            prog.chat.messages.append(message)

        if args.msg:
            prog.chat._add_message(BaseModel.create_message(ChatRoles.USER, args.msg))
        
        should_ask = has_piped_input or args.msg or args.task or args.task_file
        
        if should_ask:
            func.log("Starting direct ask.")
            ask(
                prog.llm,
                prog.chat.messages, 
                write_to_file=prog.write_to_file,
                output_filename=prog.output_filename,
                hide_think_anim=args.no_think_anim,
                print_output=args.no_out != True
            )
            sys.exit(0)
            
    def _check_nhandle_list_sessions(self, args):
        """
        Lists all active agent sessions found in the current working directory.

        :param args: The parsed command-line arguments containing the --list-sessions flag.
        :raises SystemExit: Exits after displaying the session list or a 'not found' message.
        """
        if args.list_sessions:
            sessions = AgentSessionManager.list_sessions(os.getcwd())
            if not sessions:
                func.out("No agent sessions found.", level="INFO")
                sys.exit(0)

            func.out("Agent Sessions:", level="INFO")
            for session in sessions:
                func.out(f"Session ID: {session['session_id']}, User Request: {session.get('user_request', 'N/A')}", level="INFO")
            sys.exit(0)