import xml.etree.ElementTree as ET
import json
import re
from typing import Dict, Any, Optional
import ai.functions as func


class ResponseParser:
    def __init__(self, parameter_mode: str = "xml"):
        self.parameter_mode = parameter_mode

    def _extract_params(self, element: Optional[ET.Element]) -> Dict[str, Any]:
        if element is None:
            return {}

        if self.parameter_mode == "json":
            try:
                text = (element.text or "").strip()
                return json.loads(text) if text else {}
            except json.JSONDecodeError:
                return {"error": "Invalid JSON in tool_parameters"}

        return {child.tag: (child.text or "").strip() for child in element}

    def _sanitize_block(self, xml_string: str, tag: str) -> str:
        """Extracts a block, escapes rogue characters, and returns the rebuilt string."""
        # Search for everything inside the target tags, including newlines (DOTALL)
        pattern = re.compile(f"<{tag}>(.*?)</{tag}>", re.DOTALL)
        match = pattern.search(xml_string)
        
        if not match:
            return xml_string
        
        raw_content = match.group(1)
        # Convert rogue brackets to safe XML entities
        safe_content = raw_content.replace("<", "&lt;").replace(">", "&gt;")
        
        # Stitch the safe content back into the original string
        return xml_string[:match.start(1)] + safe_content + xml_string[match.end(1):]

    def parse(self, raw_string: str) -> Dict[str, Any]:
        try:
            start = raw_string.find("<response>")
            end = raw_string.rfind("</response>")

            if start == -1 or end == -1:
                return {"status": "FAILED", "error": "Missing response boundaries"}

            xml_block = raw_string[start : end + 11].strip()

            try:
                # FIRST ATTEMPT: Strict parse
                root = ET.fromstring(xml_block)
            except ET.ParseError:
                func.log("[ResponseParser] Initial XML parsing failed, attempting salvage operation...")
                # SALVAGE OPERATION TRIGGERED
                # Sanitize the blocks where the LLM is allowed to 'think'
                xml_block = self._sanitize_block(xml_block, "thought")
                xml_block = self._sanitize_block(xml_block, "notes")
                xml_block = self._sanitize_block(xml_block, "response_to_user")
                
                # SECOND ATTEMPT: Parse the repaired string
                root = ET.fromstring(xml_block)

            def get_text(tag):
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
            # If it STILL fails, the tool parameters or structure itself is broken
            return {"status": "FAILED", "error": f"Malformed XML (Salvage Failed): {str(e)}"}
        except Exception as e:
            return {"status": "FAILED", "error": f"System Error: {str(e)}"}