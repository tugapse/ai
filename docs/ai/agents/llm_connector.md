

## 1. Architectural Role  
LLMConnector acts as a structured agentic XML communication bridge between application logic and LLMs, translating JSON inputs into XML-driven agent interactions and parsing XML outputs into structured data.  

## 2. Interface & API Surface  
| Entity | Type | Functional Responsibility |  
| :--- | :--- | :--- |  
| `LLMConnector` | Class | Manages LLM communication via XML, handling request/response cycles with dynamic constraints |  
| `send_request` | Method | Structured agentic XML communication with system prompt injection and agent config |  
| `send_raw_request` | Method | Bypasses structured parsing for raw code/text generation with explicit task_context and instruction |  
| `_execute_llm_call` | Method | Executes LLM call via temporary file output, ensuring reliable capture of streaming responses |  
| `_parse_xml_response` | Method | Tolerant XML parser with auto-repair logic, extracting structured data from XML response |  

## 3. Execution Logic & Flow  
- **Initialization**: Loads LLM instance via `__init__`, setting `self.llm` for subsequent calls  
- **Data Path**:  
  1. `send_request` reads system prompt file and injects dynamic constraints  
  2. Constructs XML messages with system prompt and JSON input context  
  3. Calls `_execute_llm_call` to stream LLM output to temporary file  
  4. `_parse_xml_response` extracts structured data from XML, handling malformed input via regex repair  
- **Conditional Branching**:  
  - `system_prompt_path` file read failure triggers error return  
  - XML parsing failure triggers debug dump and error return  
  - Missing XML tags auto-repaired via tag balancing algorithm  

## 4. Resource Dependencies  
- **Standard Libraries**: `uuid`, `os`, `re`, `xml.etree.ElementTree`, `json`  
- **Internal Modules**: `core.llms.base_llm` (for LLM interface), `functions` (for logging), `direct` (for ask function)  
- **External Packages**: None explicitly referenced  

## 5. Configuration & Environment  
- **Hardcoded Constants**:  
  - XML tag names (`<response>`, `<manifest>`, etc.)  
  - Error message strings for parsing failures  
- **Environment Lookups**: None directly accessed in provided code