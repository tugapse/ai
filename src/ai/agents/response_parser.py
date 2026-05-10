import re
import yaml
from typing import Dict, Any
import functions as func

class ResponseParser:
    """
    Parses the JARVIS Plain Text Protocol (____@ tokens).
    Robust against 8B model formatting quirks, such as unquoted special 
    characters and indentation drift.
    """
    def __init__(self):
        # Regex to find any token starting with ____@
        self.token_pattern = re.compile(r"(____@[A-Za-z_:]+)")

    def _parse_key_value_block(self, text: str) -> Dict[str, str]:
        """Helper to parse simple KEY: VALUE lines (used for Manifest)."""
        data = {}
        for line in text.strip().split('\n'):
            if ':' in line:
                key, val = line.split(':', 1)
                data[key.strip()] = val.strip()
        return data

    def _sanitize_yaml(self, yaml_str: str) -> str:
        """
        Fixes common 8B model YAML errors:
        1. Quotes unquoted special variables (like @ROOT).
        2. Normalizes inconsistent indentation drift.
        """
        # 1. Fix unquoted @ variables (e.g., paths: @ROOT -> paths: "@ROOT")
        yaml_str = re.sub(r':\s*(@[A-Za-z0-9_/.-]+)', r': "\1"', yaml_str)
        
        # 2. Fix indentation drift
        lines = yaml_str.strip().split('\n')
        fixed_lines = []
        in_multiline = False
        
        for line in lines:
            # Check if this line starts a multi-line code block (e.g., content: |)
            if re.match(r'^\s*[a-zA-Z0-9_-]+\s*:\s*\|\s*$', line):
                in_multiline = True
                fixed_lines.append(line.lstrip()) # Force key to root level
                continue
                
            if in_multiline:
                # If the model forgot to indent the code block, force a 2-space indent
                if line.strip() != "" and not re.match(r'^[ \t]+', line):
                    fixed_lines.append("  " + line)
                else:
                    fixed_lines.append(line)
            else:
                # Standard key-value line. Strip leading whitespace to force uniform 0-indent.
                fixed_lines.append(line.lstrip())
                
        return '\n'.join(fixed_lines)

    def _parse_tool_block(self, tool_header: str, content: str) -> Dict[str, Any]:
        """
        Parses the tool block which includes:
        - Tool Name (first line of the content block)
        - INTENT (optional)
        - ARGS (YAML-style, safely sanitized)
        """
        # 1. Grab the tool name from the very first line of the content
        content = content.strip()
        lines = content.split('\n', 1) # Split only on the first newline
        
        tool_name = lines[0].strip() # This successfully captures 'read_dir'
        remaining_content = lines[1] if len(lines) > 1 else ""
        
        tool_data = {
            "tool_name": tool_name,
            "tool_parameters": {},
            "intent": ""
        }

        # 2. Search the remaining content for ARGS:
        args_match = re.search(r"ARGS:\s*(.*)", remaining_content, re.DOTALL)
        
        if args_match:
            # 3. Extract INTENT if it exists before ARGS
            intent_part = remaining_content[:args_match.start()].strip()
            if "INTENT:" in intent_part:
                tool_data["intent"] = intent_part.replace("INTENT:", "").strip()
            
            # 4. Parse the ARGS safely
            try:
                args_text = args_match.group(1).strip()
                sanitized_args = self._sanitize_yaml(args_text)
                tool_data["tool_parameters"] = yaml.safe_load(sanitized_args) or {}
            except Exception as e:
                func.log(f"[Parser] Failed to parse ARGS block: {e}")
                tool_data["tool_parameters"] = {"error": f"Malformed ARGS: {str(e)}"}
        
        return tool_data

    def parse(self, raw_string: str) -> Dict[str, Any]:
        """
        Main entry point for parsing the model's raw text response.
        """
        try:
            # 1. Split the string into segments based on the ____@ tokens
            segments = self.token_pattern.split(raw_string)
            
            data_map = {}
            for i in range(1, len(segments), 2):
                token = segments[i].strip()
                content = segments[i+1].strip() if i+1 < len(segments) else ""
                data_map[token] = content

            # 2. Extract standard internal state fields
            thought = data_map.get("____@thought", "")
            notes = data_map.get("____@notes", "")
            response_to_user = data_map.get("____@response", "")
            agent_target = data_map.get("____@TARGET", "STOP").strip()

            # 3. Parse Manifest (Phase/Priority)
            manifest_text = data_map.get("____@manifest", "")
            manifest = self._parse_key_value_block(manifest_text)

            # 4. Handle the Tool Execution
            tool_token = next((k for k in data_map.keys() if k.startswith("____@tool:")), None)
            
            action = {
                "tool_name": "",
                "tool_parameters": {},
                "agent_target": agent_target
            }

            action = {
                "tool_name": "",
                "tool_parameters": {},
                "agent_target": agent_target # Extracted from ____@TARGET
            }

            if tool_token:
                tool_info = self._parse_tool_block(tool_token, data_map[tool_token])
                action["tool_name"] = tool_info["tool_name"]
                action["tool_parameters"] = tool_info["tool_parameters"]
                
                # I added 'intent' here just in case you want to log it, 
                # but it won't break your existing Orchestrator.
                action["intent"] = tool_info["intent"] 

            # The final return is 100% identical to your old XML parser
            return {
                "status": "SUCCESS",
                "thought": thought,
                "notes": notes,
                "manifest": manifest,
                "action": action, 
                "response_to_user": response_to_user
            }

        except Exception as e:
            return {"status": "FAILED", "error": f"System Error during parsing: {str(e)}"}