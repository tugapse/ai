import os
import sys
import json
import uuid
from typing import Optional


# Ensure project root is in path
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import ai.functions as func
from ai.config import ProgramSetting
from ai.services.directory_manager import DirectoryManager
from ai.tools.tool_registry import ToolRegistry
from ai.agents.llm_connector import LLMConnector
from ai.agents.agent_orchestrator import AgentOrchestrator
from ai.core.events import Events

def load_pipeline_config(prog, pipeline_file: str) -> dict:
    """
    Loads the pipeline configuration JSON file.

    This function searches for the configuration file in several locations:
    1. As a direct path if it is absolute.
    2. Relative to the user's designated pipelines directory.
    3. Relative to the system's designated pipelines directory.

    It also verifies that all referenced prompt files exist in the system prompts directory.

    Args:
        prog: The main program object, used to access configuration and directories.
        pipeline_file: The name or path of the pipeline configuration file (e.g., "my_pipeline.json").

    Returns:
        A dictionary containing the loaded configuration if successful, or an empty dictionary if loading fails.
    """
    directory = DirectoryManager()
    system_dir = directory.get_system_pipelines_directory()
    user_dir = directory.get_user_pipelines_directory()
    pipeline_file = pipeline_file.replace(".json", "")+".json"

    potential_paths = [pipeline_file]
    if os.path.isabs(pipeline_file):
        potential_paths.append(pipeline_file)
    else:
        potential_paths.append(os.path.join(user_dir, pipeline_file))
        potential_paths.append(os.path.join(system_dir, pipeline_file))

    pipeline_path = ""
    for path in potential_paths:
        if os.path.exists(path):
            pipeline_path = path
            break
    
    if not pipeline_path:
        func.error(f"Pipeline config '{pipeline_file}' not found. Checked: {potential_paths}")
        return {}
        
    try:
        with open(pipeline_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        # Verify prompt files exist
        for agent_name, agent_data in config.get("agents", {}).items():
            prompt_file = agent_data.get("prompt_file")
            if prompt_file:
                full_prompt_path = prompt_file if os.path.isabs(prompt_file) else os.path.join(directory.get_system_prompts_templates_directory(), prompt_file)
                if not os.path.exists(full_prompt_path):
                    func.error(f"Prompt file missing for agent {agent_name}: {full_prompt_path}")
                    return {}
                agent_data["prompt_file_path"] = full_prompt_path
        
        return config
    except Exception as e:
        func.error(f"Failed to parse pipeline config: {e}")
        return {}

def build_orchestrator(prog, pipeline_file: str = "default.json", io=None, directory_manager: Optional[DirectoryManager] = None) -> AgentOrchestrator:
    """
    Builds a fully wired AgentOrchestrator: pipeline config, LLM connector and
    a tool registry with system and user tools.

    Args:
        prog: The main program object (provides the LLM and module registry).
        pipeline_file: Name or path of the pipeline configuration.
        io: Optional AgentIO channel (defaults to the classic terminal output).
        directory_manager: Optional directory service (used to locate user tools).

    Returns:
        A ready-to-run AgentOrchestrator.

    Raises:
        ValueError: If the pipeline cannot be loaded or the LLM is not available.
    """
    from ai.tools.tool_loader import load_and_register_user_tools

    pipeline_config = load_pipeline_config(prog, pipeline_file)
    if not pipeline_config:
        raise ValueError(f"Failed to load pipeline config '{pipeline_file}'.")

    if not prog.llm:
        raise ValueError("LLM not initialized. Cannot proceed with agent mode.")

    connector = LLMConnector(prog.llm)
    registry = ToolRegistry()
    # Built-in tools come from the enabled tool modules (ai.modules.tools_*).
    if prog.modules is not None and hasattr(prog.modules, "tool_functions"):
        for name, tool_ref in prog.modules.tool_functions().items():
            registry.register_tool(name, tool_ref)

    # Dynamically load and register tools from the user-defined 'tools' directory
    directory_manager = directory_manager or DirectoryManager()
    load_and_register_user_tools(registry, directory_manager.get_user_tools_directory())

    return AgentOrchestrator(
        llm_connector=connector,
        tool_registry=registry,
        pipeline_config=pipeline_config,
        module_registry=prog.modules,
        io=io,
    )


class Agent(Events):
    """
    A high-level agent facade that encapsulates the full agentic loop.

    This class manages the initialization of all necessary componentssuch as the
    Tool Registry, LLM Connector, and Agent Orchestratorand provides the primary
    interface for running an agentic workflow based on a defined pipeline configuration.
    """
    def __init__(self, prog, pipeline_file: str = "default.json"):
        """
        Initializes the agent and its core components.

        Args:
            prog: The main program object, providing access to config, LLM, etc.
            pipeline_file (str): Path to the agent pipeline configuration.
        
        Raises:
            ValueError: If the agent pipeline configuration cannot be loaded.
        """
        super().__init__()
        self.prog = prog
        self.pipeline_config = load_pipeline_config(prog, pipeline_file)
        
        if not self.pipeline_config:
            raise ValueError("Failed to load agent pipeline configuration.")

        # Core Components
        self.registry = ToolRegistry() # Singleton
        
        self.llm_connector = LLMConnector(self.prog.llm)
        self.orchestrator = AgentOrchestrator(
            llm_connector=self.llm_connector,
            tool_registry=self.registry,
            pipeline_config=self.pipeline_config,
            module_registry=self.prog.modules
        )

        # Propagate events from the orchestrator up to the agent level
        self.orchestrator.add_event(self.orchestrator.EVENT_BEFORE_LLM_REQUEST, lambda data: self.trigger(self.orchestrator.EVENT_BEFORE_LLM_REQUEST, data))
        self.orchestrator.add_event(self.orchestrator.EVENT_AFTER_LLM_REQUEST, lambda data: self.trigger(self.orchestrator.EVENT_AFTER_LLM_REQUEST, data))

    def run(self, user_prompt: str, session_id: str = ""):
        """
        Starts the agent's execution loop with a given prompt.

        This method initiates the agent's turn, handles session management (creating a new ID if none is provided),
        and delegates the core execution to the orchestrator.

        Args:
            user_prompt (str): The initial user request or objective.
            session_id (str, optional): An existing session ID to resume. 
                                        If None, a new session is created.
        """
        self.trigger("before_agent_turn")
        
        if not session_id:
            session_id = str(uuid.uuid4())
            func.log(f"Starting new agent session: {session_id}")
        
        self.orchestrator.run_loop(user_prompt, session_id)
        
        self.trigger("after_agent_turn")