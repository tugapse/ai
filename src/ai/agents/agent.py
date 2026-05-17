import os
import sys
import json
import uuid


# Ensure project root is in path
# sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import ai.functions as func
from ai.config import ProgramSetting
from ai.tools.tool_registry import ToolRegistry
from ai.agents.llm_connector import LLMConnector
from ai.agents.message_orchestrator import MessageOrchestrator
from ai.core.events import Events

def load_pipeline_config(prog, pipeline_file: str) -> dict:
    """
    Loads the pipeline configuration JSON file.
    - If an absolute path is provided, it's used directly.
    - If a relative path is provided, it's first checked relative to the project root.
    - If not found, and it's a simple filename, it's then checked inside the 'pipelines' directory.
    """
    root_dir = prog.config.get(ProgramSetting.ROOT_DIRECTORY)
    pipeline_file = pipeline_file.replace(".json", "")+".json"

    potential_paths = [pipeline_file]
    if os.path.isabs(pipeline_file):
        potential_paths.append(pipeline_file)
    else:
        potential_paths.append(os.path.join(root_dir, "pipelines", pipeline_file))

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
                full_prompt_path = prompt_file if os.path.isabs(prompt_file) else os.path.join(root_dir, prompt_file)
                if not os.path.exists(full_prompt_path):
                    func.error(f"Prompt file missing for agent {agent_name}: {full_prompt_path}")
                    return {}
                agent_data["prompt_file_path"] = full_prompt_path
        
        return config
    except Exception as e:
        func.error(f"Failed to parse pipeline config: {e}")
        return {}

class Agent(Events):
    """
    A high-level agent facade that encapsulates the full agentic loop.
    """
    def __init__(self, prog, pipeline_file: str = "default.json"):
        """
        Initializes the agent and its core components.

        Args:
            prog: The main program object, providing access to config, LLM, etc.
            pipeline_file (str): Path to the agent pipeline configuration.
        """
        super().__init__()
        self.prog = prog
        self.pipeline_config = load_pipeline_config(prog, pipeline_file)
        
        if not self.pipeline_config:
            raise ValueError("Failed to load agent pipeline configuration.")

        # Core Components
        self.registry = ToolRegistry() # Singleton
        self.connector = LLMConnector(self.prog.llm)
        self.orchestrator = MessageOrchestrator(
            connector=self.connector,
            registry=self.registry,
            pipeline_config=self.pipeline_config,
            module_registry=self.prog.modules
        )

        # Propagate events from the orchestrator up to the agent level
        self.orchestrator.add_event(self.orchestrator.EVENT_BEFORE_LLM_REQUEST, lambda data: self.trigger(self.orchestrator.EVENT_BEFORE_LLM_REQUEST, data))
        self.orchestrator.add_event(self.orchestrator.EVENT_AFTER_LLM_REQUEST, lambda data: self.trigger(self.orchestrator.EVENT_AFTER_LLM_REQUEST, data))

    def run(self, user_prompt: str, session_id: str = ""):
        """
        Starts the agent's execution loop with a given prompt.

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