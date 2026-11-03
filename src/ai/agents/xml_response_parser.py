import xml.etree.ElementTree as ET
import json
import re
from typing import Dict, Any, Optional
import ai.functions as func

class ResponseParser:
    """
    Parses a raw string containing an AI response, which is expected to be wrapped
    in <response> tags and structured either as XML or JSON within its content.

    This class handles the extraction of structured data like thought processes,
    manifests, and tool action parameters from the raw input.
    """
    def __init__(self, parameter_mode: str = "xml"):
        """
        Initializes the ResponseParser.

        Args:
            parameter_mode: Specifies how to interpret tool_parameters. Can be "xml" or "json".
        """
        self.parameter_mode = parameter_mode

    def _extract_params(self, element: Optional[ET.Element]) -> Dict[str, Any]:
        """
        Extracts parameters from an XML element based on the configured parameter_mode.

        If mode is "json", it attempts to parse the element's text content as JSON.
        If mode is "xml", it iterates over child tags to build a dictionary.

        Args:
            element: The XML element containing the parameters.

        Returns:
            A dictionary containing the extracted parameters. Returns an error dict if JSON parsing fails.
        """
        if element is None:
            return {}

        if self.parameter_mode == "json":
            try:
                text = (element.text or "").strip()
                return json.loads(text) if text else {}
            except json.JSONDecodeError:
                return {"error": "Invalid JSON in tool_parameters"}

        params = {}
        for child in element:
            tag = child.tag
            text = (child.text or "").strip()
            
            if tag in params:
                if isinstance(params[tag], list):
                    params[tag].append(text)
                else:
                    params[tag] = [params[tag], text]
            else:
                params[tag] = text
                
        return params

    def _sanitize_block(self, xml_string: str, tag: str) -> str:
        """
        Extracts a specific XML block, escapes potentially rogue characters (< and >)
        within its content, and returns the rebuilt string.

        This is used as a salvage operation when initial XML parsing fails.

        Args:
            xml_string: The full XML string to search within.
            tag: The name of the tag whose content needs sanitization.

        Returns:
            The XML string with the specified block's content safely escaped.
        """
        pattern = re.compile(f"<{tag}>(.*?)</{tag}>", re.DOTALL)
        match = pattern.search(xml_string)
        
        if not match:
            return xml_string
        
        raw_content = match.group(1)
        safe_content = raw_content.replace("<", "&lt;").replace(">", "&gt;")
        
        return xml_string[:match.start(1)] + safe_content + xml_string[match.end(1):]

    def parse(self, raw_string: str) -> Dict[str, Any]:
        """
        Parses the raw string containing the AI response to extract structured data.

        It first attempts standard XML parsing. If that fails, it attempts a
        salvage operation by sanitizing specific tags before re-parsing.

        Args:
            raw_string: The complete string received from the AI agent.

        Returns:
            A dictionary containing the parsed results, including status, thought,
            manifest, action details, and the response to the user.
            If parsing fails, the status will be "FAILED" with an error message.
        """
        try:
            start = raw_string.find("<response>")
            end = raw_string.rfind("</response>")

            if start == -1 or end == -1:
                return {"status": "FAILED", "error": f"Missing response boundaries.", "response_to_user": raw_string}

            xml_block = raw_string[start : end + 11].strip()

            try:
                root = ET.fromstring(xml_block)
            except ET.ParseError:
                func.log("[ResponseParser] Initial XML parsing failed, attempting salvage operation...")
                xml_block = self._sanitize_block(xml_block, "thought")
                xml_block = self._sanitize_block(xml_block, "notes")
                xml_block = self._sanitize_block(xml_block, "response_to_user")
                root = ET.fromstring(xml_block)

            def get_text(tag):
                """Helper function to safely retrieve text content from a specific tag."""
                node = root.find(tag)
                return (node.text or "").strip() if node is not None else ""

            manifest_node = root.find("manifest")
            manifest_data = {c.tag: (c.text or "").strip() for c in manifest_node} if manifest_node is not None else {}
            
            return {
                "status": "SUCCESS",
                "thought": get_text("thought"),
                "notes": get_text("notes"),
                "manifest": manifest_data,
                "action": {
                    "tool_name": get_text("action/tool_name"),
                    "tool_parameters": self._extract_params(root.find("action/tool_parameters")),
                    "agent_target": get_text("action/agent_target"),
                },
                "response_to_user": get_text("response_to_user")
            }

        except ET.ParseError as e:
            return {"status": "FAILED", "error": f"Malformed XML (Salvage Failed): {str(e)}"}
        except Exception as e:
            return {"status": "FAILED", "error": f"System Error: {str(e)}"}