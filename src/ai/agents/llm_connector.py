import os
from typing import Callable, Dict, Any, List, Optional

import ai.functions as func
from ai.agents.xml_response_parser import ResponseParser
from ai.core.llms.base_llm import BaseModel
from ai.chat.chat import ChatRoles
from ai.direct import ask
from ai.services.directory_manager import DirectoryManager
from ai.core.llms.api_retry import LLMAPIError

# Whole-call retries when a stream drops after output started (cannot be resumed).
PARTIAL_STREAM_RETRIES = 2

class LLMConnector:
    """
    Manages the connection and communication interface with a Language Model (LLM).

    This class handles loading system prompts, configuring agent constraints,
    executing LLM calls for structured (XML) or raw text generation, and parsing
    the resulting responses using a dedicated parser.
    """
    def __init__(self, llm_instance: BaseModel, parameter_mode: str = "xml"):
        """
        Initializes the LLMConnector.

        Args:
            llm_instance: An instance of the BaseModel representing the LLM.
            parameter_mode: The mode for communication (e.g., "xml").
        """
        self.llm = llm_instance
        # Initialize the new strict parser here
        self.parser = ResponseParser()
        self.directory_manager = DirectoryManager()
        # Optional per-token callback (set by interactive UIs for live progress).
        self.on_token: Optional[Callable[[str], None]] = None
        
    def get_context_limit(self) -> int:
        """
        Retrieves the maximum context window size supported by the LLM.

        Returns:
            The maximum context window size as an integer.
        """
        return self.llm.token_info_count.max_context_window
    
    def get_max_tokens(self) -> int:
        """
        Retrieves the maximum number of tokens the LLM can generate in a single response.

        Returns:
            The maximum output token count as an integer.
        """
        return self.llm.token_info_count.max_output_tokens

    def send_request(self, json_input: Dict[str, Any], system_prompt_path: str, agent_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Sends a structured request to the LLM, typically expecting an XML response.

        The system prompt is loaded from a file, and agent constraints (tools, targets)
        are dynamically injected into the system prompt if provided in agent_config.

        Args:
            json_input: A dictionary containing the primary input context for the agent.
            system_prompt_path: The file path to the base system prompt.
            agent_config: Optional configuration dictionary containing tool definitions
                           and allowed targets for the agent.

        Returns:
            A dictionary containing the parsed result from the LLM, including status and response.
        """
        func.debug(f"Loading system prompt: {system_prompt_path}")
        
        try:
            with open(system_prompt_path, "r", encoding="utf-8") as f:
                system_content = f.read()
                self.llm.system_prompt = system_content
        except Exception as e:
            func.error(f"Failed to read prompt file: {e}")
            return {"status": "FAILED", "error": f"Prompt error: {e}"}

        if agent_config:
            system_content = system_content.replace("{{TOOLS}}", self.load_tools_descriptions(agent_config))

        # The same final prompt goes to llm.system_prompt and to the system message: some
        # backends (e.g. Jarvis) send the message, others (e.g. Gemini) read the attribute.
        system_content = self.load_system_prompt_agent_output_rules(system_content)
        self.llm.system_prompt = system_content


        messages = [
            BaseModel.create_message(ChatRoles.SYSTEM, system_content),
            BaseModel.create_message(ChatRoles.USER, f"<context>{str(json_input)}</context>"),
        ]

        attempt = 0
        while True:
            try:
                raw_response = self._execute_llm_call(messages)
                break
            except LLMAPIError as e:
                attempt += 1
                if e.transient and e.partial and attempt <= PARTIAL_STREAM_RETRIES:
                    func.log(f"LLMConnector: stream interrupted mid-response, re-running the call ({attempt}/{PARTIAL_STREAM_RETRIES}).", level="WARN")
                    continue
                # Not the model's fault: report it as an API failure, not a malformed response.
                return {"status": "FAILED", "api_error": True, "transient": e.transient, "error": e.user_message()}
        
        # Using the new strict parser
        parsed = self.parser.parse(raw_response)
        
        if parsed.get("status") == "FAILED":
            raw_Content = parsed.get("response_to_user", None)

            if not raw_Content:
                func.error(f"XML Parsing Failed: {parsed.get('error')}")
            else:
                func.out(raw_Content)
        return parsed

    def load_tools_descriptions(self, agent_config):
        allowed_tools = agent_config.get("tools", [])
        tool_descriptions = agent_config.get("tool_descriptions", "")
        allowed_targets = agent_config.get("allowed_targets", ["STOP"])
            
        injection = [
                "\n\n--- DYNAMIC CONSTRAINTS ---",
                f"AVAILABLE TOOLS:\n{tool_descriptions}" if allowed_tools else "AVAILABLE TOOLS: None.",
                f"ALLOWED AGENT TARGETS: {', '.join(allowed_targets)}",
            ]
        return "\n".join(injection)
    
    def load_system_prompt_agent_output_rules(self, system_content):
        directory_manager = DirectoryManager()
        agent_output_rules_path = os.path.join(directory_manager.get_system_dir(), "inject", "agent-out.md")
        if os.path.exists(agent_output_rules_path):
            with open(agent_output_rules_path, "r", encoding="utf-8") as f:
                agent_output_rules = f.read()
            return system_content.replace("{{AGENT_OUTPUT_RULES}}", agent_output_rules)
        
        func.debug("Agent output rules file not found. Proceeding without injecting rules.")
        return system_content.replace("{{AGENT_OUTPUT_RULES}}", "")

    
    def send_raw_request(self, payload: Dict[str, Any], system_prompt: str = "") -> str:
        """
        Bypasses structured parsing for raw code/text generation.

        This method sends a direct instruction and context to the LLM without
        applying the strict XML parsing logic.

        Args:
            payload: A dictionary containing 'task_context' and 'instruction'.
            system_prompt: The system prompt to use for this specific call.

        Returns:
            The raw string response generated by the LLM.
        """
        messages = [
            BaseModel.create_message(ChatRoles.SYSTEM, system_prompt),
            BaseModel.create_message(ChatRoles.USER, 
                f"CONTEXT:\n{payload.get('task_context')}\n\n"
                f"INSTRUCTION:\n{payload.get('instruction')}"
            )
        ]
        try:
            return self._execute_llm_call(messages).strip()
        except LLMAPIError as e:
            func.error(f"LLMConnector: raw request failed: {e.user_message()}")
            return ""

    def _execute_llm_call(self, messages: List[Dict[str, str]]) -> str:
        """
        Executes the LLM call using the underlying ask function and captures the output
        to a temporary file for reliable retrieval.

        Args:
            messages: A list of message dictionaries to send to the LLM.

        Returns:
            The content read from the output file, or an empty string if an error occurs.
        """
        output_filename = f"{os.path.join(self.directory_manager.get_system_logs_directory(), "output", 'llm_output_active.md')}"

        try:
            ask(
                self.llm, 
                messages, 
                hide_think_anim=True, 
                print_output=False, 
                output_filename=output_filename, 
                write_to_file=True,
                stream=True,
                on_token=self.on_token
            )
            
            if os.path.exists(output_filename):
                with open(output_filename, "r", encoding="utf-8") as f:
                    content = f.read()
                return content
            else:
                func.error("LLM execution finished but output file was not created.")
                return ""
                
        except LLMAPIError:
            raise
        except Exception as e:
            func.error(f"LLM Execution failed: {e}")
            if os.path.exists(output_filename):
                os.remove(output_filename)
            return ""
