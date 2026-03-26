import os
import sys
import json
import functions as func

# Ensure project root is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import ProgramSetting

from .tool_registry import ToolRegistry
from .llm_connector import LLMConnector
from .message_orchestrator import MessageOrchestrator

def load_pipeline_config(prog, pipeline_file: str) -> dict:
    """
    Loads the pipeline configuration JSON file.
    """
    root_dir = prog.config.get(ProgramSetting.ROOT_DIRECTORY)
    pipeline_path = pipeline_file if os.path.isabs(pipeline_file) else os.path.join(root_dir, pipeline_file)
    
    if not os.path.exists(pipeline_path):
        func.error(f"Pipeline config not found: {pipeline_path}")
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
    
    
