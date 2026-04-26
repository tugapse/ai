from color import Color
from response_parser import ResponseParser
import re
import xml.etree.ElementTree as ET
from typing import Dict, Any, List
import functions as func
from core.llms.base_llm import BaseModel
from chat.chat import ChatRoles
from direct import ask
import uuid
import os

class LLMConnector:
    def __init__(self, llm_instance: BaseModel, parameter_mode: str = "xml"):
        self.llm = llm_instance
        # Initialize the new strict parser here
        self.parser = ResponseParser(parameter_mode=parameter_mode)
        
    def get_context_limit(self) -> int:
        return self.llm.token_info_count.max_context_window
    
    def get_max_tokens(self) -> int:
        return self.llm.token_info_count.max_output_tokens

    def send_request(self, json_input: Dict[str, Any], system_prompt_path: str, agent_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Method for Structured Agentic XML communication."""
        func.debug(f"Loading system prompt: {system_prompt_path}")
        
        try:
            with open(system_prompt_path, "r", encoding="utf-8") as f:
                system_content = f.read()
                self.llm.system_prompt = system_content
        except Exception as e:
            func.error(f"Failed to read prompt file: {e}")
            return {"status": "FAILED", "error": f"Prompt error: {e}"}

        if agent_config:
            allowed_tools = agent_config.get("tools", [])
            tool_descriptions = agent_config.get("tool_descriptions", "")
            allowed_targets = agent_config.get("allowed_targets", ["STOP"])
            
            injection = [
                "\n\n--- DYNAMIC CONSTRAINTS ---",
                f"AVAILABLE TOOLS:\n{tool_descriptions}" if allowed_tools else "AVAILABLE TOOLS: None.",
                f"ALLOWED AGENT TARGETS: {', '.join(allowed_targets)}",

            ]
            system_content = system_content.replace(
                "# MANDATORY XML FORMAT",
            "\n".join(injection) + "\n\n# MANDATORY XML FORMAT"
            )   
            self.llm.system_prompt = system_content


        messages = [
            BaseModel.create_message(ChatRoles.SYSTEM, system_content),
            BaseModel.create_message(ChatRoles.USER, f"<context>{str(json_input)}</context>"),
        ]

        raw_response = self._execute_llm_call(messages)
        
        # Using the new strict parser
        parsed = self.parser.parse(raw_response)
        
        if parsed.get("status") == "FAILED":
            func.error(f"XML Parsing Failed: {parsed.get('error')}")
            
        return parsed

    def send_raw_request(self, payload: Dict[str, Any], system_prompt: str = "") -> str:
        """Bypasses structured parsing for raw code/text generation."""
        messages = [
            BaseModel.create_message(ChatRoles.SYSTEM, system_prompt),
            BaseModel.create_message(ChatRoles.USER, 
                f"CONTEXT:\n{payload.get('task_context')}\n\n"
                f"INSTRUCTION:\n{payload.get('instruction')}"
            )
        ]
        return self._execute_llm_call(messages).strip()

    def _execute_llm_call(self, messages: List[Dict[str, str]]) -> str:
        """Uses a unique, timestamped file to capture output reliably."""
        output_filename = f"{func.get_root_directory()}/logs/llm_output_active.md"

        try:
            ask(
                self.llm, 
                messages, 
                hide_think_anim=True, 
                print_output=False, 
                print_mode="line", 
                output_filename=output_filename, 
                write_to_file=True,
                stream=True
            )
            
            if os.path.exists(output_filename):
                with open(output_filename, "r", encoding="utf-8") as f:
                    content = f.read()
                return content
            else:
                func.error("LLM execution finished but output file was not created.")
                return ""
                
        except Exception as e:
            func.error(f"LLM Execution failed: {e}")
            if os.path.exists(output_filename):
                os.remove(output_filename)
            return ""