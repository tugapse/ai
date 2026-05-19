## 1. Architectural Role
| Name | Source file |
| :--- | :--- |
| ResponseParser | [/src/ai/agents/response_parser.py](/src/ai/agents/response_parser.py)|

The **ResponseParser** is the gateway between the JARVIS Plain Text Protocol  (____@ tokens) produced by the model and the orchestrators structured data expectations. It scans the raw model output for tokenized sections, segments and maps them into a machine-friendly dictionary that includes fields such as **thought**, **notes**, **manifest**, **action**, and **response_to_user**. 

Its role is to normalize model quirkslike indentation drift and unquoted special charactersso downstream components can reliably consume the data regardless of formatting anomalies. The parser also handles the extraction and sanitization of ARGS blocks within tool invocations, producing a safe, structured representation of tool parameters.

In the broader system, this component anchors the transition from free-form model text to the internal action model used by the orchestration layer. It feeds into the action descriptor, including tool invocation details and the agent_target, and serves as a stable surface for logging and debugging a models reasoning trace (thoughts, notes, and manifest). Downstream modules depend on the structured action payload to drive actual tool execution and state progression.

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- No hardcoded constants identified.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| **ResponseParser** | Class | Parses the JARVIS Plain Text Protocol tokens from a raw string into a structured dictionary, including extraction of thoughts, notes, manifest data, an action block (tool_name, tool_parameters, intent), and response_to_user. Handles tool blocks containing ARGS with YAML-like content via a sanitizer. |

## 4. Code Example
- Example usage:
```python
from ai.agents.response_parser import ResponseParser

raw_string = "<response>...</response>"  # LLM output string
rp = ResponseParser()
result = rp.parse(raw_string)
print(result)

```
This demonstrates how to instantiate the component and process a raw model output string into the standardized structure expected by the orchestration layer.

## 5. Execution Logic & Flow
- Initialization:
  - Compile the token_pattern regex to locate tokens starting with ____@ in the input string.
- Data Path:
  - Split the raw string into segments around token boundaries.
  - Build a data_map mapping each token to its corresponding content block.
  - Extract standard internal state fields: thought, notes, response_to_user, and agent_target.
  - Parse the Manifest block into a manifest dictionary using a simple KEY: VALUE parser.
- Conditional Branching:
  - Identify the presence of a tool block (____@tool:*). If found:
    - Use _parse_tool_block to derive tool_name, tool_parameters, and intent from the block.
    - Safely parse ARGS content via _sanitize_yaml and yaml.safe_load to populate tool_parameters.
    - If ARGS parsing fails, record an error in tool_parameters.
  - If no tool token is present, the action remains with an empty tool_name and parameters.
- Output:
  - Return a structured dictionary containing status, thought, notes, manifest, action, and response_to_user. If an error occurs, return a failure payload with an error message.

Key internal steps leverage:
- _parse_key_value_block for simple manifest lines.
- _sanitize_yaml to fix YAML-like ARGS blocks and indentation quirks.
- _parse_tool_block to extract tool_name, intent, and parameters from the tool block.

For documentation on this component and its scope, see the RESPONDER docs: [ResponseParser Documentation](/docs/ai/agents/response_parser.md).

## 6. Resource Dependencies
- **Standard Libraries**: re, yaml, typing
- **Internal Modules**: 
  - [ai.functions](/docs/ai/functions.md) (as a logging/utility hook used when ARGS parsing fails)
  - PyYAML (yaml) (used for ARGS parsing)
