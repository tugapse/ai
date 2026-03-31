import os
import json
import io
import re
from contextlib import redirect_stdout
from typing import Dict, Any, Optional

import functions as func
from color import Color
from core.llms.base_llm import BaseModel
from core.chat import ChatRoles
from direct import ask

class LLMConnector:
    def __init__(self, llm_instance: BaseModel):
        self.llm = llm_instance

    def send_request(self, json_input: Dict[str, Any], system_prompt_path: str, agent_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Existing method for Structured Agentic JSON communication."""
        func.debug(f"Sending request to agent with prompt: {system_prompt_path}")
        try:
            with open(system_prompt_path, "r", encoding="utf-8") as f:
                system_content = f.read()
        except Exception as e:
            func.error(f"Failed to read prompt file: {e}")
            return {"status": "FAILED", "error": f"Prompt error: {e}"}

        if agent_config:
            # Dynamic injection of constraints (Keep your existing logic)
            allowed_tools = agent_config.get("tools", [])
            tool_descriptions = agent_config.get("tool_descriptions", "")
            allowed_targets = agent_config.get("allowed_targets", ["STOP"])
            
            injection_lines = ["\n\n--- DYNAMIC CONSTRAINTS ---"]
            injection_lines.append(f"AVAILABLE TOOLS:\n{tool_descriptions}" if allowed_tools else "AVAILABLE TOOLS: None.")
            injection_lines.append(f"ALLOWED AGENT TARGETS: {', '.join(allowed_targets)}")
            system_content += "\n".join(injection_lines)

        messages = [
            BaseModel.create_message(ChatRoles.USER, system_content),
            BaseModel.create_message(ChatRoles.USER, json.dumps(json_input, indent=2)),
        ]

        raw_response = self._execute_llm_call(messages)
        return self._validate_json(raw_response)

    # --- NEW: RAW REQUEST FOR SPECIALISTS ---
    def send_raw_request(self, payload: Dict[str, Any], system_prompt: str = "") -> str:
        """
        NEW: Bypasses JSON validation to allow raw code/text generation.
        Used by the Specialist/Ghost workers.
        """
        func.log(f"{Color.NORMAL_CYAN}[SPECIALIST CALL]{Color.RESET} Generating raw content...", level="DEBUG")
        
        # We build a simple, direct prompt for the specialist
        messages = [
            BaseModel.create_message(ChatRoles.SYSTEM, system_prompt),
            BaseModel.create_message(ChatRoles.USER, f"CONTEXT:\n{payload.get('task_context')}\n\nINSTRUCTION:\n{payload.get('instruction')}")
        ]

        # Execute call and return the string DIRECTLY
        return self.llm.chat(messages, stream=False)

    def _execute_llm_call(self, messages: list) -> str:
        """Helper to unify the redirect_stdout logic."""
        output_buffer = io.StringIO()
        with redirect_stdout(output_buffer):
            # We use the 'ask' function from your direct.py
            ask(self.llm, messages, show_think_anim=False, print_mode="line")
        return output_buffer.getvalue()

    def _validate_json(self, raw_string: str) -> Dict[str, Any]:
        """Existing logic to clean and parse JSON blocks."""
        try:
            match = re.search(r'(\{.*\})', raw_string, re.DOTALL)
            if not match: 
                raise ValueError("No JSON object found in response.")
            
            content = match.group(1).replace('"""', '"')

            def fix_newlines(m):
                return m.group(1) + m.group(2).replace('\n', '\\n').replace('\r', '\\r') + m.group(3)

            content = re.sub(r'(\":\s*\")(.*?)(\"(?:,|\s*\}))', fix_newlines, content, flags=re.DOTALL)
            return json.loads(content, strict=False)
        except Exception as e:
            func.error(f"\n{Color.RED}[CRITICAL PARSING ERROR]:{Color.RESET} {e}")
            # Log the raw string for debugging when it fails
            func.debug(f"RAW OUTPUT THAT FAILED: {raw_string}")
            exit(1)
            return {"status": "FAILED", "error": f"Invalid JSON: {str(e)}"}