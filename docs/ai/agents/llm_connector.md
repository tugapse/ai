## 1. Architectural Role
| Name | Source file |
| :--- | :--- |
| LLMConnector | [/src/ai/agents/llm_connector.py](/src/ai/agents/llm_connector.py) |

The LLMConnector component serves as the architectural bridge between a concrete Large Language Model (LLM) implementation and a structured, XML-oriented agent workflow. It encapsulates the orchestration logic required to load system prompts, apply dynamic constraints, construct structured messages for the LLM, and parse the LLMs response using a strict XML-aware parser. Its role is to translate high-level agent intents into a format the LLM can process reliably while ensuring robust handling of prompt loading failures and parsing errors. By delegating parsing to ResponseParser, the component enforces a consistent interpretation of LLM outputs, enabling downstream modules to react to standardized results.

In the broader system, LLMConnector interacts with the LLModel abstraction (BaseModel), the XML-based response parser, and the tool/injection framework that provides dynamic constraints or tool descriptions. It operates within the execution flow that converts structured inputs into agent actions, and then back into structured results. The component is central to the data/state transition: it reads a system prompt, augments it with optional agent tool constraints, sends a formatted message sequence to the LLM, captures the raw output, and finally parses it into a structured dictionary for downstream consumption. This tight coupling with the parser and LLM interface ensures clear boundaries between message construction, prompt management, and result interpretation.

- Internal references: [ResponseParser](/docs/ai/agents/xml_response_parser.md), [BaseModel](/docs/ai/core/llms/base_llm.md), [ChatRoles](/docs/ai/chat/chat.md), [ai.functions](/docs/ai/functions.md), [ask](/docs/ai/direct.md)

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- No hardcoded constants identified.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `LLMConnector` | Class | Orchestrates LLM calls with system prompts, applies dynamic constraints, formats messages, executes the LLM call, and parses the result via the strict XML parser. |

## 4. Code Example
```python

# Example usage (pseudo-code; replace with real implementations)
from ai.agents.llm_connector import LLMConnector
from ai.core.llms.base_llm import BaseModel

# llm_impl should be an instantiated subclass of BaseModel
llm_impl = SomeLLMImplementation()

connector = LLMConnector(llm_impl)

# Prepare inputs
json_input = {"task": "summarize", "context": {"user": "example"}}

system_prompt_path = "/path/to/system_prompt.md"

agent_config = {
    "tools": ["tool_a", "tool_b"],
    "tool_descriptions": "tool_a: does X; tool_b: does Y",
    "allowed_targets": ["STOP", "EXECUTE"]
}

response = connector.send_request(json_input, system_prompt_path, agent_config=agent_config)

print(response)
```

## 5. Execution Logic & Flow
- Initialization:
  - Create LLMConnector with an LLM instance (BaseModel derivative).
  - Initialize a ResponseParser for strict parsing.

- Data Path:
  - Read system prompt from system_prompt_path, assign to llm.system_prompt.
  - If agent_config is provided, construct a dynamic constraints block with available tools and allowed targets and append to the system prompt.
  - Build messages list:
    - System message containing the system prompt.
    - User message containing the input context as <context>...</context>.
  - Execute LLM call via _execute_llm_call(messages).
  - Parse raw LLM output with the strict XML parser (self.parser.parse).
  - If parsing indicates failure, log error and return the parsed error structure.

- Conditional Branching:
  - If prompt file read fails, return a failure dictionary with the error.
  - If parsing fails, log an error but return the parsed error result.

## 6. Resource Dependencies
- **Standard Libraries**: os, typing
- **Internal Modules**: 
  - [ai.functions](/docs/ai/functions.md) 
  - [ResponseParser](/docs/ai/agents/xml_response_parser.md)
  - [BaseModel](/docs/ai/core/llms/base_llm.md)
  - [ChatRoles](/docs/ai/chat/chat.md)
  - [ask](/docs/ai/direct.md)
  - [LLMConnector](/docs/ai/agents/llm_connector.md)
- **External Packages**: None