import os
import json
import io
import re
from contextlib import redirect_stdout
from typing import Dict, Any

import functions as func
from color import Color
from core.llms.base_llm import BaseModel
from core.chat import ChatRoles
from direct import ask

class LLMConnector:
    def __init__(self, llm_instance: BaseModel):
        self.llm = llm_instance

    def send_request(self, json_input: Dict[str, Any], system_prompt_path: str, agent_config: Dict[str, Any] = None) -> Dict[str, Any]:
        func.debug(f"Sending request to agent with prompt: {system_prompt_path}")
        try:
            with open(system_prompt_path, "r", encoding="utf-8") as f:
                system_content = f.read()
        except Exception as e:
            func.error(f"Failed to read prompt file: {e}")
            return {"status": "FAILED", "error": f"Prompt error: {e}"}

        # Dynamically inject constraints into the system prompt
        if agent_config:
            allowed_tools = agent_config.get("tools", [])
            tool_descriptions = agent_config.get("tool_descriptions", "")
            allowed_targets = agent_config.get("allowed_targets", ["STOP"])
            
            injection_lines = ["\n\n--- DYNAMIC CONSTRAINTS ---"]
            if allowed_tools and tool_descriptions:
                injection_lines.append(f"AVAILABLE TOOLS:\n{tool_descriptions}")
            else:
                injection_lines.append("AVAILABLE TOOLS: None. You cannot use tools.")
            
            injection_lines.append(f"ALLOWED AGENT TARGETS: {', '.join(allowed_targets)}")
            injection_lines.append("If you change agents, provide a 'message_to_target' in your 'action' block to instruct them.")
            injection_lines.append("---------------------------")
            system_content += "\n".join(injection_lines)

        messages = [
            BaseModel.create_message(ChatRoles.SYSTEM, system_content),
            BaseModel.create_message(ChatRoles.USER, json.dumps(json_input, indent=2)),
        ]

        output_buffer = io.StringIO()
        agent_name = os.path.splitext(os.path.basename(system_prompt_path))[0].upper()
        func.log(f"[*] Active Agent: {agent_name}")

        with redirect_stdout(output_buffer):
            ask(self.llm, messages, show_think_anim=True, print_mode="token")

        raw_response = output_buffer.getvalue()
        return self._validate_json(raw_response)

    def _validate_json(self, raw_string: str) -> Dict[str, Any]:
        try:
            # Strip out everything outside the markdown-like JSON block if generated
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
            return {"status": "FAILED", "error": f"Invalid JSON: {str(e)}"}