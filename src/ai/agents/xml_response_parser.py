import xml.etree.ElementTree as ET
import json
import re
from typing import Dict, Any, Optional
import ai.functions as func

class ResponseParser:
    """
    Parses a raw string containing an AI response, which is expected to be wrapped
    in <response> tags and structured either as XML or JSON within its content.
    """
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

    def _preprocess_xml(self, xml_string: str) -> str:
        """
        Cleans common LLM XML formatting errors and safely strips CDATA wrappers
        before attempting standard XML parsing.
        """
        xml_string = xml_string.replace('\xa0', ' ')
        xml_string = re.sub(r'</\s*([a-zA-Z0-9_]+)\s*>', r'</\1>', xml_string)
        xml_string = re.sub(r'<\s*([a-zA-Z0-9_]+)\s*>', r'<\1>', xml_string)

        def escape_cdata(match):
            content = match.group(1)
            return content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            
        xml_string = re.sub(r'<!\[CDATA\[(.*?)\]\]>', escape_cdata, xml_string, flags=re.DOTALL)
        xml_string = re.sub(r'&(?!(?:[a-zA-Z]+|#[0-9]+|#x[0-9a-fA-F]+);)', '&amp;', xml_string)

        return xml_string

    def _sanitize_block(self, xml_string: str, tag: str) -> str:
        pattern = re.compile(f"<{tag}>(.*?)</{tag}>", re.DOTALL)
        match = pattern.search(xml_string)
        
        if not match:
            return xml_string
        
        raw_content = match.group(1)
        safe_content = raw_content.replace("<", "&lt;").replace(">", "&gt;")
        
        return xml_string[:match.start(1)] + safe_content + xml_string[match.end(1):]

    def _sanitize_tool_params(self, xml_string: str) -> str:
        """
        Escapes rogue < and > characters inside individual <tool_parameters> child tags
        (e.g., bash redirects like 2>/dev/null or code snippets in patch parameters)
        when the model forgets to wrap them in CDATA.
        """
        if self.parameter_mode == "json":
            return self._sanitize_block(xml_string, "tool_parameters")

        def sanitize_inner(match):
            inner = match.group(1)
            sanitized = re.sub(
                r"<([a-zA-Z0-9_]+)>(.*?)</\1>",
                lambda m: f"<{m.group(1)}>{m.group(2).replace('<', '&lt;').replace('>', '&gt;')}</{m.group(1)}>",
                inner,
                flags=re.DOTALL
            )
            return f"<tool_parameters>{sanitized}</tool_parameters>"

        return re.sub(r"<tool_parameters>(.*?)</tool_parameters>", sanitize_inner, xml_string, flags=re.DOTALL)

    def parse(self, raw_string: str) -> Dict[str, Any]:
        try:
            start = raw_string.find("<response>")
            end = raw_string.rfind("</response>")

            if start == -1 or end == -1:
                return {"status": "FAILED", "error": "Missing response boundaries.", "response_to_user": raw_string}

            xml_block = raw_string[start : end + 11].strip()
            xml_block = self._preprocess_xml(xml_block)

            try:
                root = ET.fromstring(xml_block)
            except ET.ParseError:
                func.log("[ResponseParser] Initial XML parsing failed, attempting block sanitization...")
                xml_block = self._sanitize_block(xml_block, "thought")
                xml_block = self._sanitize_block(xml_block, "notes")
                xml_block = self._sanitize_block(xml_block, "response_to_user")
                xml_block = self._sanitize_tool_params(xml_block)
                
                try:
                    root = ET.fromstring(xml_block)
                except ET.ParseError as e:
                    return {"status": "FAILED", "error": f"Malformed XML (Salvage Failed): {str(e)}"}

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

        except Exception as e:
            return {"status": "FAILED", "error": f"System Error: {str(e)}"}