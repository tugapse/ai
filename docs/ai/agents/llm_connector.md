## Module Purpose
This file defines the `LLMConnector` class, which facilitates communication with a Large Language Model (LLM) by sending structured XML requests or raw text requests and handling the parsing of the LLM's responses, including auto-repair for malformed XML.

## Interface & Exports
*   `LLMConnector`: A class designed to connect to and interact with an LLM instance.
    *   `__init__(self, llm_instance: BaseModel)`: Initializes the connector with an LLM instance.
    *   `send_request(self, json_input: Dict[str, Any], system_prompt_path: str, agent_config: Dict[str, Any] = None) -> Dict[str, Any]`: Sends a structured request, loads a system prompt, injects agent configuration, and parses the XML response.
    *   `send_raw_request(self, payload: Dict[str, Any], system_prompt: str = "") -> str`: Sends a raw text generation request without structured parsing.

## Internal Logic
The `LLMConnector` class manages LLM interactions. The `send_request` method constructs messages by loading a system prompt from `system_prompt_path`, optionally injecting `agent_config` details (tools, targets, descriptions) into the system prompt, and then converting `json_input` into a `<context>` XML tag. It calls `_execute_llm_call` to get the LLM's raw response and then `_parse_xml_response` to process it. The `send_raw_request` method constructs messages from `payload`'s `task_context` and `instruction` and directly returns the raw LLM output.

The `_execute_llm_call` method manages the actual LLM interaction by generating a unique temporary filename (`llm_output_{unique_id}.tmp`), calling the `direct.ask` function to write the LLM's response to this file, reading the content, and then deleting the temporary file.

The `_parse_xml_response` method is a tolerant XML parser. It first uses `re.search` to find a complete `<response>...</response>` block. If the block is incomplete or missing, it attempts to auto-repair the XML by matching open and close tags and appending missing closing tags, ensuring `</response>` is present. It then uses `xml.etree.ElementTree` to parse the (potentially repaired) XML. It defines two helper functions: `extract_text` to extract text content, preserving inner XML tags as string data, and `extract_struct` to recursively convert XML elements into Python dictionaries or lists. Finally, it extracts specific fields like `thought`, `notes`, `manifest`, `action` (with `tool_name`, `tool_parameters`, `agent_target`, `task_for_target`, `message_to_target`), and `response_to_user` into a dictionary. It attempts to `json.loads` the `manifest` if it's not already a dictionary. Error handling includes logging and a debug dump for fatal parsing errors.

## Dependencies
*   `re`
*   `xml.etree.ElementTree` (aliased as `ET`)
*   `typing`
*   `functions` (aliased as `func`)
*   `core.llms.base_llm.BaseModel`
*   `core.chat.ChatRoles`
*   `direct.ask`
*   `uuid`
*   `os`
*   `json` (imported locally within `_parse_xml_response`)

## Constants & Environment
*   `output_filename` pattern: `llm_output_{unique_id}.tmp` is a hardcoded format for temporary files.
*   The `injection` list in `send_request` contains hardcoded string components for dynamic constraints within the system prompt.