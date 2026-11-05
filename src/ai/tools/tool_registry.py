import json
import re
from typing import Dict, Any, Callable, Optional
import ai.functions as func


class ToolRegistry:
    """
    Manages the registration, retrieval, and execution of available tools (functions).

    This class implements the Singleton pattern to ensure only one instance
    of the tool registry exists application-wide, providing a centralized
    point of access for all callable functions exposed to the AI agent.
    """
    _instance = None
    _tools: Dict[str, Callable]

    def __new__(cls):
        """
        Controls the instantiation of the class, ensuring it adheres to the Singleton pattern.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools = {}
        return cls._instance

    def __init__(self):
        """
        Initializes the ToolRegistry instance.
        """
        pass

    def register_tool(self, name: str, func_ref: Callable):
        """
        Registers a callable function with a unique name in the registry.

        Args:
            name: The unique string identifier for the tool.
            func_ref: The actual callable function object to be registered.
        """
        self._tools[name] = func_ref
        func.debug(f"Tool registered: {name}", level="WARN")

    def get_tool_info(self, name: str) -> str:
        """
        Retrieves a formatted string containing the name and documentation of a registered tool.

        Args:
            name: The name of the tool to query.

        Returns:
            A formatted string describing the tool, or a message indicating it is not found.
        """
        if name not in self._tools:
            return f"- {name}: No description available."

        doc = self._tools[name].__doc__ or "No description provided."
        indented_doc = doc.strip().replace("\n", "\n  ")
        return f"- {name}:\n  {indented_doc}"

    def execute_tool(self, name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a registered tool function with the provided parameters.

        Args:
            name: The name of the tool to execute.
            params: A dictionary containing keyword arguments for the tool function.

        Returns:
            A dictionary containing the execution status and result or error.
        """
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
        """
        Returns the full dictionary of registered tool functions.

        Returns:
            A dictionary mapping tool names (str) to their callable references (Callable).
        """
        return self._tools  # or self._tools, whichever dict holds your functions

    @staticmethod
    def parse_docstring_to_schema(func_name: str, func_ref: Callable) -> dict:
        """
        Dynamically translates Python docstrings into an LLM-friendly JSON Schema.

        This method parses the docstring, extracts descriptions, and infers parameter types
        from the 'Args:' section. It enforces a mandatory 'intent' property for latent reasoning.

        Args:
            func_name: The name of the function being documented.
            func_ref: The callable function object whose docstring is to be parsed.

        Returns:
            A dictionary conforming to a schema structure suitable for LLM tool definition.
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
        Constructs the system access manual using a generic protocol format.

        This method iterates over all registered tools, converts their Python docstrings
        into standardized JSON Schemas, and formats them into a readable string
        suitable for inclusion in the system prompt provided to the LLM.

        Args:
            all_tools: A dictionary containing all registered tool names and their callable references.

        Returns:
            A multi-line string containing the complete tool access manual.
        """
        if not all_tools:
            return ""

        manual = "\n\n[PROTOCOL: SYSTEM ACCESS]\n"
        for name, ref in all_tools.items():
            # If ref is a callable, parse it. If it's already a dict, use it directly.
            schema = (
                ToolRegistry.parse_docstring_to_schema(name, ref)
                if callable(ref)
                else ref
            )

            f_name = schema.get("name", name)
            f_desc = schema.get("description", "No description provided.")
            f_returns = schema.get("returns", "Standard status dictionary.")
            f_params = json.dumps(schema.get("parameters", {}))

            manual += f"Function: {f_name} | Desc: {f_desc} | Returns: {f_returns} | Schema: {f_params}\n"

        manual += ToolRegistry.get_tool_usage_rule()
        return manual

    @staticmethod
    def parse_manual_tags(text: str) -> Optional[dict]:
        """
        Standardized regex parser for catching tool triggers in the streaming text output.

        This method attempts to parse tool calls from various proprietary or standardized
        formats (YAML, J.A.R.V.I.S. tags, Gemma artifacts). It handles complex nested structures
        and quote escaping to reliably extract the tool name and arguments.

        Args:
            text: The raw text chunk received from the LLM stream.

        Returns:
            A dictionary representing a function call if successfully parsed, or None if no tool call is detected or parsing fails.
        """

        # 1. YAML Format parser via ResponseParser
        if "____@tool_end" in text:
            from ai.agents.response_parser import ResponseParser
            parser = ResponseParser()
            parsed = parser.parse(text)
            if parsed and parsed.get("action") and parsed["action"].get("tool_name"):
                return {
                    "type": "function_call",
                    "name": parsed["action"]["tool_name"],
                    "args": parsed["action"]["tool_parameters"]
                }
            else:
                func.log(f"DEBUG: YAML tool parse failed. Text: {text}", level="DEBUG")

        # 2. Matches J.A.R.V.I.S. tags AND Gemma's <|tool_call> artifacts
        pattern = r"(?:\s*____@tool|\s*____@|\s*<\|?tool_call\|?>)\s*(?:call:)?(\w+)\s*(\{)"
        match = re.search(pattern, text, re.DOTALL)

        if match:
            name = match.group(1)
            start_index = match.start(2)
            
            brace_count = 0
            in_string = False
            in_single_string = False
            escape_next = False
            in_gemma_string = False
            raw_args = None
            
            i = start_index
            while i < len(text):
                char = text[i]
                
                if escape_next:
                    escape_next = False
                    i += 1
                    continue
                    
                if char == '\\':
                    escape_next = True
                    i += 1
                    continue
                    
                if text[i:i+5] == '<|"|>':
                    in_gemma_string = not in_gemma_string
                    i += 5
                    continue
                
                if text[i:i+3] == '<|"':
                    in_gemma_string = True
                    i += 3
                    continue

                if text[i:i+3] == '"|>':
                    in_gemma_string = False
                    i += 3
                    continue
                    
                if char == '"' and not in_gemma_string and not in_single_string:
                    in_string = not in_string
                    i += 1
                    continue

                if char == "'" and not in_gemma_string and not in_string:
                    in_single_string = not in_single_string
                    i += 1
                    continue
                    
                if not in_string and not in_single_string and not in_gemma_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            raw_args = text[start_index:i+1]
                            break
                i += 1
                
            if not raw_args:
                # If we haven't found a matching closing brace, it's either an incomplete 
                # streaming chunk or malformed output. Return None to allow stream buffering.
                return None

            # 1. Clean Gemma's weird quote artifacts and escape inner quotes safely
            def escape_inner_quotes(m):
                import json
                return json.dumps(m.group(1))

            clean_args = re.sub(r'(?:<\|"\|>|<\|")(.*?)(?:<\|"\|>|"\|>)', escape_inner_quotes, raw_args, flags=re.DOTALL)

            # 2. Fix unquoted JSON keys (kept for legacy support, though yaml handles it)
            clean_args = re.sub(r"([{,]\s*)([a-zA-Z0-9_]+)\s*:", r'\1"\2":', clean_args)

            try:
                import yaml
                parsed_args = yaml.safe_load(clean_args)

                # Pop the 'intent' key so it doesn't crash Python functions
                if isinstance(parsed_args, dict) and "intent" in parsed_args:
                    del parsed_args["intent"]

                return {"type": "function_call", "name": name, "args": parsed_args}
            except Exception as e:
                func.log(
                    f"DEBUG: JSON parse fallback triggered for {name}. Error: {e}",
                    level="DEBUG",
                )
                return {
                    "type": "function_call",
                    "name": name,
                    "args": {"raw": raw_args},
                }

        return None

    @staticmethod
    def get_tool_usage_rule():
        return """
# [CRITICAL RULE: TOOL CALLING]
The `____@tool` token is the starting point for the system to call a tool.

1. You have NO direct access to the environment or system state unless you use a tool.
2. To use a tool, you MUST use the following multi-line format:
   ____@tool: [tool_name]
   INTENT: [Your reasoning for this specific call]
   ARGS:
     [string_param]: "value"
     [list_param]:
       - "item_1"
       - "item_2"
     [code_param]: |
       [multi-line code or content]
   ____@tool_end
3. DO NOT use XML tags or JSON arrays. Use standard YAML block lists (with dashes) for arrays.
4. You MUST explicitly close the tool block with the ____@tool_end token. Do not write anything after it until the tool returns a result.
"""
