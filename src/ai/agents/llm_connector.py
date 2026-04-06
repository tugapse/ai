import os
import json
import io
import re
from typing import Dict, Any, Optional, List
import tempfile

import functions as func
from color import Color
from core.llms.base_llm import BaseModel
from core.chat import ChatRoles
from direct import ask

class LLMConnector:
    def __init__(self, llm_instance: BaseModel):
        self.llm = llm_instance

    def send_request(self, json_input: Dict[str, Any], system_prompt_path: str, agent_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Method for Structured Agentic JSON communication."""
        func.debug(f"Loading system prompt: {system_prompt_path}")
        
        try:
            with open(system_prompt_path, "r", encoding="utf-8") as f:
                system_content = f.read()
        except Exception as e:
            func.error(f"Failed to read prompt file: {e}")
            return {"status": "FAILED", "error": f"Prompt error: {e}"}

        if agent_config:
            # Dynamic injection of constraints
            allowed_tools = agent_config.get("tools", [])
            tool_descriptions = agent_config.get("tool_descriptions", "")
            allowed_targets = agent_config.get("allowed_targets", ["STOP"])
            
            injection = [
                "\n\n--- DYNAMIC CONSTRAINTS ---",
                f"AVAILABLE TOOLS:\n{tool_descriptions}" if allowed_tools else "AVAILABLE TOOLS: None.",
                f"ALLOWED AGENT TARGETS: {', '.join(allowed_targets)}"
            ]
            system_content += "\n".join(injection)

        messages = [
            BaseModel.create_message(ChatRoles.SYSTEM, system_content),
            BaseModel.create_message(ChatRoles.USER, json.dumps(json_input, indent=2)),
        ]

        raw_response = self._execute_llm_call(messages)
        return self._validate_json(raw_response)

    def send_raw_request(self, payload: Dict[str, Any], system_prompt: str = "") -> str:
        """
        Bypasses JSON validation for raw code/text generation.
        Used by Specialist/Ghost workers for high-fidelity output.
        """
        func.debug(f"Specialist call initiated with role: {system_prompt[:50]}...")
        
        messages = [
            BaseModel.create_message(ChatRoles.SYSTEM, system_prompt),
            BaseModel.create_message(ChatRoles.USER, 
                f"CONTEXT:\n{payload.get('task_context')}\n\n"
                f"INSTRUCTION:\n{payload.get('instruction')}"
            )
        ]

        # We use the same execution helper to ensure consistent stdout handling
        return self._execute_llm_call(messages).strip()

    def _execute_llm_call(self, messages: List[Dict[str, str]]) -> str:
        """Unifies the LLM execution and captures output to a file."""
        # Create a temporary file to capture output cleanly, avoiding stdout redirection.
        with tempfile.NamedTemporaryFile(mode='w+', delete=True, encoding='utf-8') as tmp_file:
            try:
                # Using 'ask' from direct.py, directing output to a temp file.
                ask(self.llm, messages, hide_think_anim=True, print_output=False, print_mode="line", output_filename=tmp_file.name, write_to_file=True)
                tmp_file.seek(0)  # Go back to the beginning of the file to read it.
                return tmp_file.read()
            except Exception as e:
                func.error(f"LLM Execution failed: {e}")
                return ""

    def _validate_json(self, raw_string: str) -> Dict[str, Any]:
        """Cleans and parses JSON blocks from raw LLM output."""
        try:
            # Look for JSON between braces, potentially inside markdown blocks
            match = re.search(r'(\{.*\})', raw_string, re.DOTALL)
            if not match: 
                func.error(f"Parser could not find a valid JSON object in response. \n{raw_string}")
                return {"status": "FAILED", "error": "No JSON object found."}
            
            content = match.group(1).replace('"""', '"')

            # Helper to escape literal newlines inside JSON string values
            def fix_newlines(m):
                return m.group(1) + m.group(2).replace('\n', '\\n').replace('\r', '\\r') + m.group(3)

            # Look for "key": "value" patterns and fix newlines in the value part
            content = re.sub(r'(\":\s*\")(.*?)(\"(?:,|\s*\}))', fix_newlines, content, flags=re.DOTALL)

            return json.loads(content, strict=False)
            
        except Exception as e:
            func.error(f"JSON Parsing Error: {e}")
            func.debug(f"FAILED RAW CONTENT:\n{raw_string}")
            # Return failure status instead of exiting to allow agent recovery
            return {"status": "FAILED", "error": f"JSON Decode Error: {str(e)}"}