import re
import xml.etree.ElementTree as ET
from typing import Dict, Any, List
import functions as func
from core.llms.base_llm import BaseModel
from core.chat import ChatRoles
from direct import ask
import uuid
import os

class LLMConnector:
    def __init__(self, llm_instance: BaseModel):
        self.llm = llm_instance

    def send_request(self, json_input: Dict[str, Any], system_prompt_path: str, agent_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """Method for Structured Agentic XML communication."""
        func.debug(f"Loading system prompt: {system_prompt_path}")
        
        try:
            with open(system_prompt_path, "r", encoding="utf-8") as f:
                system_content = f.read()
        except Exception as e:
            func.error(f"Failed to read prompt file: {e}")
            return {"status": "FAILED", "error": f"Prompt error: {e}"}

        if agent_config:
            allowed_tools = agent_config.get("tools", [])
            tool_descriptions = agent_config.get("tool_descriptions", "")
            allowed_targets = agent_config.get("allowed_targets", ["STOP"])
            
            injection = [
                "\n\n--- DYNAMIC CONSTRAINTS ---",
                f"AVAILABLE TOOLS:\n{tool_descriptions}" if allowed_tools else "AVAILABLE TOOLS: None.",
                f"ALLOWED AGENT TARGETS: {', '.join(allowed_targets)}",
                "\nIMPORTANT: You must respond in XML format. Do not use Markdown code blocks."
            ]
            system_content += "\n".join(injection)

        # Note: We send the input context as XML-wrapped text for better LLM adherence
        messages = [
            BaseModel.create_message(ChatRoles.SYSTEM, system_content),
            BaseModel.create_message(ChatRoles.USER, f"<context>{str(json_input)}</context>"),
        ]

        raw_response = self._execute_llm_call(messages)
        return self._parse_xml_response(raw_response)

    def send_raw_request(self, payload: Dict[str, Any], system_prompt: str = "") -> str:
        """Bypasses structured parsing for raw code/text generation."""
        messages = [
            BaseModel.create_message(ChatRoles.SYSTEM, system_prompt),
            BaseModel.create_message(ChatRoles.USER, 
                f"CONTEXT:\n{payload.get('task_context')}\n\n"
                f"INSTRUCTION:\n{payload.get('instruction')}"
            )
        ]
        return self._execute_llm_call(messages).strip()



    def _execute_llm_call(self, messages: List[Dict[str, str]]) -> str:
        """Uses a unique, timestamped file to capture output reliably."""
        
        # Generate a truly unique filename for this specific turn
        unique_id = uuid.uuid4().hex
        output_filename = f"llm_output_{unique_id}.tmp"
        
        try:
            # Pass the filename directly to your ask function
            # We assume ask() supports 'output_filename' (as seen in your original code)
            ask(
                self.llm, 
                messages, 
                hide_think_anim=True, 
                print_output=False, 
                print_mode="line", 
                output_filename=output_filename, 
                write_to_file=True
            )
            
            # Read the file content
            if os.path.exists(output_filename):
                with open(output_filename, "r", encoding="utf-8") as f:
                    content = f.read()
                # Clean up the file immediately
                os.remove(output_filename)
                return content
            else:
                func.error("LLM execution finished but output file was not created.")
                return ""
                
        except Exception as e:
            func.error(f"LLM Execution failed: {e}")
            # Clean up if file exists despite error
            if os.path.exists(output_filename):
                os.remove(output_filename)
            return ""

    def _parse_xml_response(self, raw_string: str) -> Dict[str, Any]:
            """Tolerant XML parser that auto-repairs truncated or malformed XML."""
            import json  # Used for safe parsing of stringified manifest data

            try:
                # 1. Directly extract the <response>...</response> block to bypass markdown wrappers
                match = re.search(r'<response[\s\S]*?</response>', raw_string)
                
                if match:
                    xml_content = match.group(0)
                else:
                    # No closing tag found → attempt recovery
                    start = raw_string.find("<response")
                    if start == -1:
                        func.error(f"Parser could not find <response> start.")
                        return {"status": "FAILED", "error": "No <response> start tag found."}

                    xml_content = raw_string[start:].strip()
                    xml_content = re.sub(r'```[a-zA-Z]*\s*$', '', xml_content).strip()

                    func.error("⚠ XML was incomplete — attempting auto-repair")

                    open_tags = re.findall(r'<([a-zA-Z0-9_]+)(?=[ >/])', xml_content)
                    close_tags = re.findall(r'</([a-zA-Z0-9_]+)>', xml_content)
                    open_tags = [t for t in open_tags if not re.search(fr'<{t}[^>]*/>', xml_content)]

                    missing = []
                    for tag in open_tags:
                        if close_tags.count(tag) < open_tags.count(tag):
                            missing.append(tag)

                    for tag in reversed(missing):
                        xml_content += f"</{tag}>"

                    if not xml_content.endswith("</response>"):
                        xml_content += "</response>"

                # 3. Parse repaired XML
                root = ET.fromstring(xml_content)

                # 4. Content Extractors

                def extract_text(el):
                    """Extracts raw text, retaining inner HTML/XML tags safely as string data."""
                    if el is None:
                        return None
                    if len(el) == 0:
                        return (el.text or "").strip()
                    
                    inner_text = el.text or ""
                    for child in el:
                        inner_text += ET.tostring(child, encoding="unicode")
                    return inner_text.strip()

                def extract_struct(el):
                    """Extracts structural XML into a Python dictionary."""
                    if el is None:
                        return None
                    children = list(el)
                    if children:
                        return {child.tag.strip(): extract_struct(child) for child in children}
                    return (el.text or "").strip()

                # 5. Safety catch for Orchestrator to ensure manifest is ALWAYS a dictionary
                manifest_data = extract_struct(root.find("manifest"))
                
                if not isinstance(manifest_data, dict):
                    # If LLM wrote JSON inside the manifest tag instead of XML, auto-parse it
                    try:
                        manifest_data = json.loads(manifest_data) if manifest_data else {}
                    except Exception:
                        manifest_data = {}
                if not isinstance(manifest_data, dict):
                    manifest_data = {}  # Bulletproof fallback

                # 6. Build structured output
                parsed = {
                    "thought": extract_text(root.find("thought")),
                    "notes": extract_text(root.find("notes")),
                    "manifest": manifest_data,
                    "action": {
                        "tool_name": extract_text(root.find("action/tool_name")),
                        "tool_parameters": extract_struct(root.find("action/tool_parameters")),
                        "agent_target": extract_text(root.find("action/agent_target")),
                        "task_for_target": extract_text(root.find("action/task_for_target")),
                        "message_to_target": extract_text(root.find("action/message_to_target")),
                    },
                    "response_to_user": extract_text(root.find("response_to_user"))
                }

                return parsed

            except Exception as e:
                func.error(f"XML Parsing Error: {e}")
                
                # --- DEBUGGING DUMP & PAUSE ---
                print("\n" + "="*60)
                print("🚨 FATAL XML PARSE ERROR - DEBUG DUMP 🚨")
                print("="*60)
                print("RAW STRING FROM LLM:")
                print("-" * 60)
                print(raw_string)
                print("\n" + "="*60)
                
                if 'xml_content' in locals():
                    print("ATTEMPTED REPAIRED XML (Failed to parse):")
                    print("-" * 60)
                    print(xml_content)
                    print("="*60 + "\n")
                
                # Pause execution until you press Enter
                input("Press ENTER to acknowledge and continue, or Ctrl+C to abort...")
                # ------------------------------

                return {"status": "FAILED", "error": f"XML Decode Error: {str(e)}"}