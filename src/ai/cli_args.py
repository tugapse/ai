"""
This module provides command-line interface (CLI) arguments parsing and processing.
It coordinates the JARVIS behavior mode: Standalone, Server, or Client.
"""

import argparse
import os
import sys

import uuid
import traceback
import re
from typing import Optional

# Configuration and Enums
from modules.server.brain_hub import BrainHub
from model_config_manager import ModelConfigManager
from config import ProgramConfig, ProgramSetting 
from entities.model_enums import ModelType

# Core logic
from chat.chat import ChatRoles
from core.llms.base_llm import BaseModel
from color import Color, format_text
from direct import ask

# Agent logic
from agents.agent import MessageOrchestrator, LLMConnector, ToolRegistry, load_pipeline_config
from agents.tool_loader import load_and_register_user_tools
import agents.agent_tools as agent_tools

import functions as func

class CliArgs:
    """
    Main orchestrator for CLI input. Handles mode dispatching 
    and ensures proper initialization based on the user's intent.
    """

    def parse_args(self, prog, args, args_parser: argparse.ArgumentParser) -> None:
        """
        The main dispatcher. Analyzes arguments to decide if JARVIS 
        acts as a Brain (Server), a Body (Client), or a Standalone agent.
        """
        # 1. System/Global Actions
        self._handle_create_tool(args)
        self._handle_config_generation(prog, args, args_parser) 
        self._is_install(args)
        self._is_print_chat(args)
        self._is_list_models(args)

        # 2. Mode Dispatching
        # Check for Server Mode (Main PC)
        if hasattr(args, 'server') and args.server:
            self._handle_server_mode(prog, args)
            os._exit(0)

        # Check for Client Mode (Tiny PC)
        if hasattr(args, 'remote') and args.remote:
            self._handle_client_mode(prog, args)
            # Fall through to execute agent/direct logic via the remote connector

        # Default to Local/Direct Task Mode
        self._handle_local_direct_mode(prog, args)

        # 3. Execution Dispatching
        if args.agent:
            self._handle_agent_mode(prog, args)
            os._exit(0) 

        self._has_message(prog, args) 
    def _handle_create_tool(self, args):
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

            user_tools_dir = os.path.join(func.get_root_directory(), "tools")
            func.ensure_directory_exists(user_tools_dir)

            file_path = os.path.join(user_tools_dir, filename)

            if os.path.exists(file_path):
                func.error(f"Tool file already exists: {file_path}")
                sys.exit(1)

            # Using double braces {{ }} for literal braces in the generated code
            skeleton_content = f"""
from agents.agent_tools import tool

@tool
def {function_name}(argument: str) -> str:
    \"\"\"A brief description of what this tool does.

    Args:
        argument (str): A description of the argument.

    Returns:
        str: A description of the return value.
    \"\"\"
    try:
        # We use quadruple braces here because this will be an f-string inside the generated file
        result = f"Executing {function_name} with: {{argument}}"

        return {{"status": "SUCCESS", "result": result}}
    except Exception as e:
        return {{"status": "FAILED", "error": str(e)}}
"""
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(skeleton_content.strip())
                
                # Fixed the escaping for the log message as well
                func.log(f"{Color.GREEN}[+] Tool skeleton created successfully at: {file_path}{Color.RESET}")

            except Exception as e:
                func.error(f"Failed to create tool file: {e}")
                sys.exit(1)
            
            sys.exit(0)


    def _handle_server_mode(self, prog, args):
        if args.server:
            try:
                orchestrator = prog.models 
                
                if args.model:
                    try:
                        orchestrator.load(args.model)
                    except Exception as e:
                        func.log(f"{{Color.RED}}[ ! ] Neural Load Failed: {{e}}. Starting in STANDBY.{{Color.RESET}}")
                else:
                    func.log(f"{{Color.CYAN}}[*] Neural Hub: Standby Mode. Awaiting Neural Link...{{Color.RESET}}")
                
                from modules.server.server_module import JarvisServerModule
                server = JarvisServerModule( 
                    host=prog.config.get("SERVER_HOST", "0.0.0.0"),
                    port=prog.config.get("SERVER_PORT", 9999),
                    brain_hub=BrainHub(prog.config) 
                )
                
                server.initialize(prog.config, orchestrator, prog.history)
                server.start()
                
            except KeyboardInterrupt:
                func.log(f"\\n{{Color.YELLOW}}[ * ] Manual override engaged. Terminating JARVIS server.{{Color.RESET}}")
                sys.exit(0)
                

    def _handle_client_mode(self, prog, args):
        """
        Swaps the local LLM for a Remote Connector to use the Main PC's GPU.
        """
        func.log(format_text("=== REMOTE BRAIN LINK ACTIVE ===", Color.YELLOW))
        
        remote_url = args.remote
        # Replace the local LLM with the Remote Link
        from modules.client.remote_connector import RemoteBrainConnector
        
        # We manually inject the remote connector into the program
        prog.llm = RemoteBrainConnector(url=remote_url, model_id=args.model)
        prog.llm_initialized = True # Mark as initialized to prevent lazy-loading local weights

    def _handle_local_direct_mode(self, prog, args):
        """
        The standard non-agent loop for one-shot tasks and context loading.
        """
        self._has_output_files(prog, args)
        self._has_image(prog, args) 
        self._has_folder(prog, args)
        self._has_file(prog, args)
        self._has_task_file(prog, args)
        self._has_task(prog, args)
        

    # --- Logic Implementations ---

    def _handle_agent_mode(self, prog, args):
        """Handles the execution of the agent pipeline."""
        # check and load for task file
        taskfile=""
        if args.task_file:
             taskfile = func.read_file(args.task_file)
             
        user_input = taskfile or args.task or ""
        if not sys.stdin.isatty():
            piped_input = sys.stdin.read().strip()
            if piped_input:
                if user_input : user_input += "\n" + piped_input
                else:  user_input = piped_input
        user_input = user_input + args.msg if args.msg else user_input

        if not user_input :
            func.error("Agent mode requires a prompt. Use --msg, --task, or pipe input.")
            sys.exit(1)

        pipeline_path = args.pipeline or "pipelines/pipeline.json"
        pipeline_config = load_pipeline_config(prog, pipeline_path)

        if not pipeline_config:
            func.error("Failed to load pipeline config. Aborting.")
            sys.exit(1)

        connector = LLMConnector(prog.llm)
        
        registry = ToolRegistry()
        for name, tool_ref in agent_tools.AVAILABLE_TOOLS.items():
            registry.register_tool(name, tool_ref)

        # Dynamically load and register tools from the user-defined 'tools' directory
        user_tools_dir = os.path.join(func.get_root_directory(), "tools")
        load_and_register_user_tools(registry, user_tools_dir)
       
        session_id = args.session_id or str(uuid.uuid4())
        func.log(f"Session: {session_id}")

        orchestrator = MessageOrchestrator(
            connector=connector, 
            registry=registry, 
            pipeline_config=pipeline_config,
            module_registry=prog.modules
        )
        
        try:
            orchestrator.run_loop(user_prompt=user_input, session_id=session_id)
        except Exception as e:
            func.error(f"Orchestrator Error: {e}")
            func.error(traceback.format_exc())
        finally:
            sys.exit(0)

    def _handle_config_generation(self, prog, args, parser: argparse.ArgumentParser):
        if not args.generate_config:
            return

        if not args.model_type:
            parser.error("The --generate-config flag requires --model-type.")

        try:
            model_type_enum = ModelType(args.model_type)
            config_filename = args.generate_config if args.generate_config.endswith(".json") else f"{args.generate_config}.json"
            
            models_dir = prog.config.get(ProgramSetting.PATHS_MODEL_CONFIGS) or os.path.join(func.get_root_directory(), "models")
            func.ensure_directory_exists(models_dir)

            full_filepath = os.path.join(models_dir, config_filename)
            new_config = ModelConfigManager.generate_default_config(model_name=args.generate_config, model_type=model_type_enum)

            ModelConfigManager.save_config(new_config, full_filepath) 
            print(format_text(f"\nConfiguration saved to: {full_filepath}", Color.GREEN))
        except Exception as e:
            func.error(f"Config generation failed: {e}")
        sys.exit(0)

    def _is_print_chat(self, args):
        if not args.print_chat:
            return
        from pathlib import Path
        from extras.console import ConsoleChatReader 
        
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
        if args.install:
            import importlib.util
            root = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])),"..","..")
            installer_path = os.path.join(root, "scripts", "install_engines.py")
            spec = importlib.util.spec_from_file_location("install_engines", installer_path)
            installer_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(installer_module)
            installer_module.main_menu()
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
                prog.chat._add_message(BaseModel.create_message(ChatRoles.USER, f"Filename: {file_obj.filename} \nContent:\n```{file_obj.content}\n"))

    def _has_file(self, prog, args):
        if args.file:
            for file_path in args.file.split(","):
                text_content = func.read_file(file_path.strip())
                prog.chat._add_message(BaseModel.create_message(ChatRoles.USER, f"Filename: {file_path.strip()} \nContent:\n```{text_content}```"))

    def _has_image(self, prog, args):
        if args.image:
            for file_path in args.image.split(","):
                path = file_path.strip()
                if os.path.exists(path):
                    prog.chat.images.append(path)
                else:
                    raise FileNotFoundError(f"Image not found: {path}")

    def _has_task_file(self, prog, args):
        if args.task_file:
            prog.chat._add_message(BaseModel.create_message(ChatRoles.SYSTEM, func.read_file(args.task_file)))

    def _has_task(self, prog, args):
        if args.task:
            task_name = f"{args.task.replace('.md', '')}.md"
            user_tasks_dir = prog.config.get(ProgramSetting.PATHS_TASKS_TEMPLATES)
            found_path = os.path.join(user_tasks_dir, task_name) if user_tasks_dir else None
            
            if not found_path or not os.path.exists(found_path):
                raise FileNotFoundError(f"Task template '{args.task}' not found.")

            prog.chat._add_message(BaseModel.create_message(ChatRoles.USER, func.read_file(found_path)))
            
    def _has_message(self, prog, args):
        piped = False
        user_input = args.task or args.msg

        if not sys.stdin.isatty():
            piped = True
            user_input = sys.stdin.read().strip()
            prog.chat._add_message(BaseModel.create_message(ChatRoles.USER, user_input))

        if prog.chat.images:
            message = prog.llm.load_images(prog.chat.images)
            prog.chat.messages.append(message)

        if args.msg:
            prog.chat._add_message(BaseModel.create_message(ChatRoles.USER, args.msg))
        
        if piped or (user_input and user_input.strip()):
            func.log("Starting direct ask.")
            ask(
                prog.llm,
                prog.chat.messages, 
                write_to_file=prog.write_to_file,
                output_filename=prog.output_filename,
                hide_think_anim=args.no_think_anim,
                print_output=args.no_out != True
            )
            os._exit(0)