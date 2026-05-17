import json
import re
from typing import Dict, Any, Callable, Optional
import functions as func

class ToolRegistry:
    _instance = None
    _tools: Dict[str, Callable]

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools = {}
        return cls._instance

    def __init__(self):
        pass

    def register_tool(self, name: str, func_ref: Callable):
        self._tools[name] = func_ref
        func.debug(f"Tool registered: {name}", level="WARN")
        
    def get_tool_info(self, name: str) -> str:
        if name not in self._tools:
            return f"- {name}: No description available."
        
        doc = self._tools[name].__doc__ or "No description provided."
        indented_doc = doc.strip().replace("\n", "\n  ")
        return f"- {name}:\n  {indented_doc}"

    def execute_tool(self, name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if name not in self._tools:
            return {"status": "FAILED", "error": f"Tool '{name}' does not exist."}
    
        try:
            p = params if isinstance(params, dict) else {}
            func.log(f"Calling tool [{name}] with: {p}")
            return self._tools[name](**p)
        except Exception as e:
            func.debug(f"Tool execution failed: {e}")
            return {"status": "FAILED", "error": str(e)}
    
    def get_all_tools(self) -> dict:
        """Returns the full dictionary of registered tool functions."""
        return self._tools  # or self._tools, whichever dict holds your functions
    


    @staticmethod
    def parse_docstring_to_schema(func_name: str, func_ref: Callable) -> dict:
        """
        Dynamically translates Python docstrings into an LLM-friendly JSON Schema.
        Enforces a mandatory 'intent' property for latent reasoning.
        """
        doc = func_ref.__doc__ or "No description provided."
        lines = [line.strip() for line in doc.strip().split("\n")]

        description = ""
        properties = {
            "intent": {
                "type": "string",
                "description": "Clear reasoning of why this tool is being called and the expected outcome.",
            }
        }
        required = ["intent"]

        state = "desc"
        for line in lines:
            if not line:
                continue

            if line.startswith("Args:"):
                state = "args"
                continue
            elif line.startswith("Returns:"):
                state = "returns"
                continue

            if state == "desc":
                description += line + " "
            elif state == "args":
                # Matches: param_name (type): description
                match = re.match(r"^(\w+)\s*\(([^)]+)\)\s*:\s*(.*)$", line)
                if match:
                    p_name, p_type, p_desc = match.groups()

                    json_type = "string"
                    if "int" in p_type.lower():
                        json_type = "integer"
                    elif "bool" in p_type.lower():
                        json_type = "boolean"
                    elif "list" in p_type.lower():
                        json_type = "array"

                    properties[p_name] = {
                        "type": json_type,
                        "description": p_desc.strip(),
                    }

                    if "optional" not in p_type.lower():
                        required.append(p_name)

        return {
            "name": func_name,
            "description": description.strip(),
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }

    @staticmethod
    def format_tools_for_prompt(all_tools: dict) -> str:
        """
        Constructs the system access manual using a generic protocol.
        Safely handles missing keys for legacy or hardcoded tool schemas.
        """
        if not all_tools:
            return ""

        manual = "\n\n[PROTOCOL: SYSTEM ACCESS]\n"
        for name, ref in all_tools.items():
            # If ref is a callable, parse it. If it's already a dict, use it directly.
            schema = (
                ToolRegistry.parse_docstring_to_schema(name, ref) if callable(ref) else ref
            )
            
            f_name = schema.get('name', name)
            f_desc = schema.get('description', 'No description provided.')
            f_returns = schema.get('returns', 'Standard status dictionary.')
            f_params = json.dumps(schema.get('parameters', {}))
            
            manual += f"Function: {f_name} | Desc: {f_desc} | Returns: {f_returns} | Schema: {f_params}\n"
        
        manual += (
            "\n[CRITICAL RULE: TOOL CALLING]\n"
            "1. You have NO direct access to the environment or system state unless you use a tool.\n"
            "2. To use a tool, you MUST output: ____@tool call:name{\"intent\":\"your reasoning\", \"param_name\":\"value\"}\n"
            "3. DO NOT use XML tags or alternate markers. Only ____@tool is valid.\n"
            "4. Stop writing immediately after the tool call closing brace.\n"
            "5. Only call ONE tool per response turn.\n"
        )
        return manual

    @staticmethod
    def parse_manual_tags(text: str) -> Optional[dict]:
        """Standardized regex parser for catching tool triggers in the stream."""
        
        # Matches J.A.R.V.I.S. tags AND Gemma's <|tool_call> artifacts
        pattern = r"(?:____@tool|____@|<\|?tool_call\|?>)\s*(?:call:)?(\w+)\s*(\{.*?\})"
        match = re.search(pattern, text, re.DOTALL)
        
        if match:
            name, raw_args = match.group(1), match.group(2)
            
            # 1. Clean Gemma's weird quote artifacts
            clean_args = raw_args.replace('<|"|>', '"').replace('<|"', '"').replace('"|>', '"')
            
            # 2. Fix unquoted JSON keys (e.g., {content: "..."} -> {"content": "..."})
            clean_args = re.sub(r'([{,]\s*)([a-zA-Z0-9_]+)\s*:', r'\1"\2":', clean_args)
            
            try:
                # 3. Use strict=False to forgive literal newlines inside strings
                parsed_args = json.loads(clean_args, strict=False)
                
                # Pop the 'intent' key so it doesn't crash Python functions
                if isinstance(parsed_args, dict) and "intent" in parsed_args:
                    del parsed_args["intent"]
                    
                return {"type": "function_call", "name": name, "args": parsed_args}
            except Exception as e:
                import functions as func
                func.log(f"DEBUG: JSON parse fallback triggered for {name}. Error: {e}", level="DEBUG")
                return {"type": "function_call", "name": name, "args": {"raw": raw_args}}
                
        return None

    

