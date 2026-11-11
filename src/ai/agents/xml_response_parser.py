import xml.etree.ElementTree as ET
import html
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

    # ------------------------------------------------------------------ parsing

    TOP_LEVEL_TAGS = ("thought", "manifest", "notes", "action", "response_to_user")
    FREE_TEXT_TAGS = ("thought", "notes", "response_to_user")
    ACTION_FIELDS = ("tool_name", "agent_target", "message_to_target", "task_for_target")
    NULL_VALUES = ("", "null", "none", "nil", "n/a")

    def parse(self, raw_string: str) -> Dict[str, Any]:
        """
        Parses an agent response.

        1. Strict: a complete <response>...</response> block (with CDATA/escaping salvage).
        2. Re-wrap: the wrapper is missing or truncated; wrap the known tags and parse again.
        3. Field extraction: pull each known field out individually (tolerates code fences,
           a missing <action> wrapper, a truncated last tag, rogue markup).

        Only fails when no usable instruction is found: no tool call, no agent target
        and no response_to_user.
        """
        try:
            raw_string = raw_string or ""
            text = self._strip_noise(raw_string)

            start = text.find("<response>")
            end = text.rfind("</response>")
            strict_error = "Missing response boundaries."
            if start != -1 and end != -1 and end > start:
                result, strict_error = self._parse_xml_block(text[start:end + len("</response>")])
                if result is not None:
                    return result

            # --- Recovery ---------------------------------------------------
            warnings = [strict_error]
            extracted = self._extract_fields(text)
            block = self._candidate_block(text)
            rewrapped = self._parse_xml_block(block)[0] if block else None

            if rewrapped is not None:
                result = self._merge(rewrapped, extracted)
                warnings.append("Recovered by re-wrapping known tags.")
            else:
                result = extracted
                warnings.append("Recovered by field extraction.")

            if self._has_instruction(result):
                result["recovered"] = True
                result["warnings"] = warnings
                func.debug(f"[ResponseParser] {warnings[-1]} ({strict_error})")
                return result

            return {
                "status": "FAILED",
                "error": f"{strict_error} No tool call, agent target or response_to_user could be recovered.",
                "response_to_user": raw_string,
            }

        except Exception as e:
            return {"status": "FAILED", "error": f"System Error: {str(e)}"}

    # ------------------------------------------------------------------ strict XML

    def _parse_xml_block(self, xml_block: str):
        """Parses a <response> block with ElementTree. Returns (result | None, error)."""
        xml_block = self._preprocess_xml(xml_block.strip())
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
                return None, f"Malformed XML (Salvage Failed): {str(e)}"

        def get_text(tag):
            node = root.find(tag)
            return (node.text or "").strip() if node is not None else ""

        manifest_node = root.find("manifest")
        manifest_data = {c.tag: (c.text or "").strip() for c in manifest_node} if manifest_node is not None else {}

        action = {
            "tool_name": get_text("action/tool_name"),
            "tool_parameters": self._extract_params(root.find("action/tool_parameters")),
            "agent_target": get_text("action/agent_target"),
        }
        for extra in ("message_to_target", "task_for_target"):
            value = get_text(f"action/{extra}")
            if value:
                action[extra] = value

        return {
            "status": "SUCCESS",
            "thought": get_text("thought"),
            "notes": get_text("notes"),
            "manifest": manifest_data,
            "action": action,
            "response_to_user": get_text("response_to_user"),
        }, ""

    # ------------------------------------------------------------------ recovery helpers

    @staticmethod
    def _strip_noise(text: str) -> str:
        """Removes markdown code fences and leaked <think> blocks around the payload."""
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"```[a-zA-Z]*[ \t]*\n?", "", text)
        return text.replace("\ufeff", "")

    def _candidate_block(self, text: str) -> str:
        """Wraps everything from the first known top-level tag in a <response> element."""
        positions = [m.start() for m in re.finditer(r"<\s*(?:response|%s)\s*>" % "|".join(self.TOP_LEVEL_TAGS), text)]
        if not positions:
            return ""
        body = text[min(positions):]
        body = re.sub(r"</?\s*response\s*>", "", body)
        last_close = max((body.rfind(f"</{t}>") + len(f"</{t}>") for t in self.TOP_LEVEL_TAGS if f"</{t}>" in body), default=-1)
        if last_close > 0:
            body = body[:last_close]
        return f"<response>{body}</response>"

    @staticmethod
    def _clean_value(value: str) -> str:
        """Strips CDATA wrappers (or unescapes entities when there is no CDATA)."""
        value = value.strip()
        if "<![CDATA[" in value:
            value = re.sub(r"<!\[CDATA\[(.*?)(?:\]\]>|$)", r"\1", value, flags=re.DOTALL)
            return value.strip()
        return html.unescape(value).strip()

    def _find_tag(self, text: str, tag: str, stop_tags=()) -> Optional[re.Match]:
        """
        Finds <tag>...</tag>. If the closing tag is missing (truncated output), the
        content runs until the next stop tag or the end of the text.
        """
        match = re.search(rf"<\s*{tag}\s*>(.*?)<\s*/\s*{tag}\s*>", text, flags=re.DOTALL)
        if match:
            return match
        stops = "|".join(stop_tags) if stop_tags else None
        pattern = rf"<\s*{tag}\s*>(.*?)(?=<\s*/?\s*(?:{stops}|response)\s*>|$)" if stops else rf"<\s*{tag}\s*>(.*)$"
        return re.search(pattern, text, flags=re.DOTALL)

    def _extract_fields(self, text: str) -> Dict[str, Any]:
        """Regex-based extraction of every known field, tolerant to broken structure."""
        # Hide CDATA payloads so tags quoted inside them are never matched.
        cdata: list = []

        def stash(m):
            cdata.append(m.group(0))
            return f"\x00{len(cdata) - 1}\x00"

        masked = re.sub(r"<!\[CDATA\[.*?(?:\]\]>|$)", stash, text, flags=re.DOTALL)
        restore = lambda v: re.sub(r"\x00(\d+)\x00", lambda m: cdata[int(m.group(1))], v)

        fields: Dict[str, str] = {}
        others = [t for t in self.TOP_LEVEL_TAGS]
        for tag in self.FREE_TEXT_TAGS:
            match = self._find_tag(masked, tag, [t for t in others if t != tag])
            if match:
                fields[tag] = self._clean_value(restore(match.group(1)))
                # Blank the block so its prose can't be mistaken for structure.
                masked = masked[:match.start()] + " " * (match.end() - match.start()) + masked[match.end():]

        manifest: Dict[str, str] = {}
        manifest_match = self._find_tag(masked, "manifest", [t for t in others if t != "manifest"])
        if manifest_match:
            for child in re.finditer(r"<\s*([a-zA-Z0-9_]+)\s*>(.*?)<\s*/\s*\1\s*>", manifest_match.group(1), flags=re.DOTALL):
                manifest[child.group(1)] = self._clean_value(restore(child.group(2)))

        action_match = self._find_tag(masked, "action", [t for t in others if t != "action"])
        action_text = action_match.group(1) if action_match else masked  # tolerate a missing <action> wrapper

        action: Dict[str, Any] = {"tool_name": "", "tool_parameters": {}, "agent_target": ""}
        for field in self.ACTION_FIELDS:
            m = re.search(rf"<\s*{field}\s*>(.*?)<\s*/\s*{field}\s*>", action_text, flags=re.DOTALL)
            if m:
                action[field] = self._clean_value(restore(m.group(1)))

        params_match = self._find_tag(action_text, "tool_parameters", ("agent_target", "message_to_target", "task_for_target", "action"))
        if params_match:
            action["tool_parameters"] = self._extract_params_text(restore(params_match.group(1)))

        return {
            "status": "SUCCESS",
            "thought": fields.get("thought", ""),
            "notes": fields.get("notes", ""),
            "manifest": manifest,
            "action": action,
            "response_to_user": fields.get("response_to_user", ""),
        }

    def _extract_params_text(self, inner: str) -> Dict[str, Any]:
        """tool_parameters children from raw text (same shape as _extract_params)."""
        if self.parameter_mode == "json":
            try:
                body = self._clean_value(inner)
                return json.loads(body) if body else {}
            except json.JSONDecodeError:
                return {"error": "Invalid JSON in tool_parameters"}

        params: Dict[str, Any] = {}
        for m in re.finditer(r"<\s*([a-zA-Z0-9_]+)\s*>(.*?)<\s*/\s*\1\s*>", inner, flags=re.DOTALL):
            tag, value = m.group(1), self._clean_value(m.group(2))
            if tag in params:
                params[tag] = params[tag] + [value] if isinstance(params[tag], list) else [params[tag], value]
            else:
                params[tag] = value
        return params

    @staticmethod
    def _merge(primary: Dict[str, Any], fallback: Dict[str, Any]) -> Dict[str, Any]:
        """Fills fields left empty by the XML parse with the regex-extracted ones."""
        merged = dict(primary)
        for key in ("thought", "notes", "response_to_user"):
            if not merged.get(key) and fallback.get(key):
                merged[key] = fallback[key]
        if not merged.get("manifest") and fallback.get("manifest"):
            merged["manifest"] = fallback["manifest"]
        action = dict(merged.get("action") or {})
        for key, value in (fallback.get("action") or {}).items():
            if value and not action.get(key):
                action[key] = value
        merged["action"] = action
        return merged

    def _has_instruction(self, result: Dict[str, Any]) -> bool:
        """Critical info: a real tool call, an agent target, or a reply to the user."""
        action = result.get("action") or {}
        tool = str(action.get("tool_name") or "").strip().lower()
        target = str(action.get("agent_target") or "").strip()
        reply = str(result.get("response_to_user") or "").strip()
        return (tool not in self.NULL_VALUES) or bool(target) or bool(reply)
