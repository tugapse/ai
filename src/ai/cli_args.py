"""
This module provides command-line interface (CLI) arguments parsing and processing.
It coordinates the JARVIS behavior mode: Standalone, Server, or Client.
"""

import argparse
import os
import sys

import uuid
import traceback
from typing import Optional

# Configuration and Enums
from ai.agents.session_manager import AgentSessionManager
from ai.modules.server.brain_hub import BrainHub
from ai.modules.server.relay import is_self_relay, normalize_relay_url
from ai.services.process_manager import ProcessManager
from ai.config import ProgramConfig, ProgramSetting 

# Core logic
from ai.chat.chat import ChatRoles
from ai.core.llms.base_llm import BaseModel
from ai.color import Color
from ai.direct import ask
from ai.stdin_reader import read_piped_stdin

# Agent logic
from ai.agents.agent import AgentOrchestrator, LLMConnector, ToolRegistry, load_pipeline_config, build_orchestrator
from ai.program import Program
from ai.services.directory_manager import DirectoryManager
from ai.tools.tool_loader import load_and_register_user_tools

import ai.cli as cli
import ai.functions as func



def _local_endpoint(host: str, port) -> str:
    """URL a client on this machine uses to reach the server (a wildcard bind is reachable on loopback)."""
    if host in ("", "0.0.0.0", "::"):
        host = "127.0.0.1"
    if ":" in host and not host.startswith("["):
        host = f"[{host}]"
    return f"http://{host}:{port}"


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
        # 1. Commands that need no model: each lives in its group module (ai/cli/<group>.py)
        cli.run_maintenance(prog, args, directory_manager)
        self._is_print_chat(args)

        # 2. Mode Dispatching
        # Check for Server Mode (Main PC)
        if getattr(args, 'server', False) or getattr(args, 'relay', None):
            self._handle_server_mode(prog, args)
            os._exit(0)

        cli.run_after_model(prog, args, directory_manager)

        # Default to Local/Direct Task Mode
        self._handle_local_direct_mode(prog, args,directory_manager=directory_manager)

        # 3. Execution Dispatching
        if args.agent or getattr(args, "resume", None) is not None:
            self._handle_agent_mode(prog, args, directory_manager)
            os._exit(0) 

        self._has_message(prog, args) 
    






    def _handle_server_mode(self, prog:Program, args):
        """
        Initializes and starts the JARVIS server mode.

        :param prog: The main program instance containing configuration and models.
        :param args: The parsed arguments, which must contain the --server flag.
        :raises KeyboardInterrupt: Catches Ctrl+C to gracefully shut down the server.
        """
        if args.server or getattr(args, "relay", None):
            try:
                host = prog.config.get(ProgramSetting.SERVER_HOST, "0.0.0.0")
                port = prog.config.get(ProgramSetting.SERVER_PORT, 9999)
                relay = normalize_relay_url(getattr(args, "relay", None) or prog.config.get(ProgramSetting.SERVER_RELAY_URL))
                if relay and is_self_relay(relay, host, port):
                    func.error(f"Relay URL {relay} is this server ({host}:{port}): it would send requests to itself. "
                               f"Point --relay at the Brain Server machine.")
                    sys.exit(2)

                brain_hub = BrainHub(prog.config, relay_url=relay)
                brain_hub.orchestrator = prog.models
                if relay:
                    func.out(f"{Color.CYAN}[*] Relay mode: agents and tools run here, inference -> {relay}{Color.RESET}")
                    try:
                        health = brain_hub.relay_health()
                        remote_level = health.get("api_level")
                        from ai.modules.server.services.frontend import API_LEVEL
                        if remote_level is not None and remote_level != API_LEVEL:
                            func.out(f"Brain Server api_level {remote_level} differs from this one ({API_LEVEL}).",
                                     level="WARNING")
                        func.out(f"Brain Server online (model: {health.get('model')}, "
                                 f"available: {', '.join(health.get('available') or []) or 'none'}).")
                    except Exception as e:
                        func.out(f"Brain Server at {relay} is not reachable yet ({e}); requests will retry it.",
                                 level="WARNING")
                if args.model:
                    try:
                        # Through the hub, so it knows which model is loaded and can swap it later.
                        brain_hub.get_brain(args.model, "")
                    except Exception as e:
                        func.error(f"Neural Load Failed: {e}. Starting in STANDBY.")
                else:
                    func.out(f"{Color.CYAN}[*] Neural Hub: Standby Mode. Awaiting Neural Link...{Color.RESET}")
                # Frees the GPU after SERVER_IDLE_UNLOAD_MINUTES without use (not in relay mode).
                brain_hub.start_idle_unloader()

                # Tool modules (filesystem, shell, web, ...) back the /api/v1/agent runs.
                if prog.modules:
                    try:
                        prog.modules.load_all()
                    except Exception as e:
                        func.error(f"Server: loading modules failed, agent runs will lack their tools: {e}")

                from ai.modules.server.server_module import JarvisServerModule
                server = JarvisServerModule(
                    host=host,
                    port=port,
                    brain_hub=brain_hub,
                    modules=prog.modules,
                )
                
                server.initialize(prog.config, prog.models, prog.history)
                ProcessManager.set_state("endpoint", _local_endpoint(server.host, server.port))
                brain_hub._publish_activity()  # "idle (<model>)": start() blocks until shutdown
                server.start()
                
            except KeyboardInterrupt:
                func.out(f"\n{Color.YELLOW}[ * ] Manual override engaged. Terminating JARVIS server.{Color.RESET}")
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
        if getattr(args, "resume", None) is not None:
            resumed = self._resolve_resume_session(args)
            if not resumed:
                sys.exit(0)
            args.session_id = resumed

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
        piped_input = read_piped_stdin(bool(user_input or args.msg))
        if piped_input:
            user_input = f"{user_input}\n{piped_input}" if user_input else piped_input
        user_input = user_input + args.msg if args.msg else user_input

        pipeline_path = args.pipeline or "default.json"

        if not user_input:
            # Interactive terminal and no prompt: open the agent chat.
            if sys.stdin.isatty() and sys.stdout.isatty() and not args.output_file:
                self._handle_agent_chat(prog, args, directory_manager, pipeline_path)
                sys.exit(0)
            func.error("Agent mode requires a prompt. Use --msg, --task, or pipe input.")
            sys.exit(1)

        from ai.agents.chat_ui.oneshot import run_one_shot

        session_id = args.session_id or str(uuid.uuid4())
        func.log(f"Session: {session_id}")

        try:
            run_one_shot(prog, user_input, pipeline=pipeline_path, session_id=session_id,
                         directory_manager=directory_manager)
        except ValueError as e:
            func.error(f"{e} Aborting.")
            sys.exit(1)
        except Exception as e:
            func.error(f"Orchestrator Error: {e}")
            func.error(traceback.format_exc())
        sys.exit(0)

    def _resolve_resume_session(self, args) -> Optional[str]:
        """
        Resolves --resume into a session id: an explicit id/prefix, or an interactive pick
        from the agent sessions of the current working directory.

        :param args: The parsed command-line arguments (uses --resume).
        :return: The session id to resume, or None when there is nothing to resume or the user cancelled.
        :raises SystemExit: On an unknown/ambiguous id, or when a picker is needed without a terminal.
        """
        from ai.agents.chat_ui.session_picker import pick_session, resolve_session_id

        sessions = AgentSessionManager.list_sessions_detailed(os.getcwd())
        query = (args.resume or "").strip()

        if query:
            try:
                session_id = resolve_session_id(sessions, query)
            except ValueError as e:
                func.error(str(e))
                sys.exit(1)
            if not session_id:
                func.error(f"No agent session matching '{query}' in {os.getcwd()}. Use 'ai sessions list' to see them.")
                sys.exit(1)
            return session_id

        if not sessions:
            func.out(f"No agent sessions found for {os.getcwd()}.", level="INFO")
            return None

        if not (sys.stdin.isatty() and sys.stdout.isatty()):
            func.error("'ai agent --resume' without an id needs an interactive terminal. Use 'ai sessions list' and 'ai agent --resume <id>'.")
            sys.exit(1)

        session_id = pick_session(sessions)
        if not session_id:
            func.out("Resume cancelled.", level="INFO")
        return session_id

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
        has_other_input = bool(args.msg or args.task or args.task_file or prog.chat.messages)
        piped_input = read_piped_stdin(has_other_input)
        has_piped_input = bool(piped_input)
        if has_piped_input:
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
            




