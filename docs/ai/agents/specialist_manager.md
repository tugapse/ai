## 1. Architectural Role
| Name | Source file |
| :--- | :--- |
| **SpecialistManager** | [/src/ai/agents/specialist_manager.py](/src/ai/agents/specialist_manager.py) |

The **SpecialistManager** serves as a dedicated orchestrator for high-complexity, unstructured generation tasks by delegating work to specialized LLM workers configured via specialist_config. It encapsulates the lifecycle of a specialist invocation: gathering the current file state, constructing a task-specific context, and sending a narrowly scoped payload to a worker through a provided connector. By isolating specialist tasks from the generic orchestration logic, it enables scalable handling of patching, writing, and other non-trivial content transformations while preserving a clean separation of concerns in the overall system.

This component integrates with the broader AI tooling ecosystem, notably relying on path resolution utilities and a generic connector to communicate with LLM workers. It references and coexists with other modules like attorney tools for path normalization, and the docs reference for specialist tooling, ensuring consistent cross-module behavior. See [agent_tools](/docs/ai/tools/agent_tools.md) for path-resolution utilities and the current modules documentation at [SpecialistManager](/docs/ai/agents/specialist_manager.md) for contextual guidance.

- Best Usage: This specialist is designed for small agent models as this will remove the System Parsing rules from the output, allowing the LLM to focus on the actual content.

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- No hardcoded constants identified.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `SpecialistManager` | Class | Coordinates invocation of specialist LLM workers using a configured role and parameters; resolves current file state, builds a task_context payload, and returns raw text output from the worker. |

## 4. Code Example
```python
# Example usage of SpecialistManager

from ai.agents.specialist_manager import SpecialistManager

# Mock connector that implements send_raw_request
class MockConnector:
    def send_raw_request(self, payload, system_prompt=None):
        return ["mocked worker response"]

connector = MockConnector()

specialist_config = {
  # { TASK_TYPE    :  SYSTEM_PROMPT_FOR_TASK                     }
    {"generate_doc": "Technical Writer. Deep-dive documentation."}
}

manager = SpecialistManager(connector, specialist_config)

params = {
    "instructions": "Update documentation for file X",
    # or "content": "old content"
    "path": "/src/example.py",
}

output = manager.invoke("patch_file", params)

print(output)
```
## Under the hood this will be used 
```python

goal = params.get("instructions") or params.get("content") or params.get("replace") or "Complete task."
path = params.get("path", "unknown")

current_state = "File does not exist yet or is empty."

... # load current_state from path or use the provided one

worker_payload = {
    "task_context": f"File Target: {path}\n\nCurrent State:\n{current_state}\n\nGoal:\n{goal}",
    "instruction": "Output raw text only. Do not use markdown blocks or explanations."
}

connector.send_raw_request(worker_payload, system_prompt=role_description)
... # Sanityze and return the content
```

## 5. Execution Logic & Flow
- Initialization:
  - __init__ stores the provided connector and specialist_config as self.connector and self.config.
- Data Path:
  - Goal is extracted from params via "instructions" (or "content"/"replace" as fallbacks).
  - Path is read (default "unknown"); an attempt is made to resolve the path with _resolve_path and to load the current file state up to 3000 characters if the file exists.
- Conditional Branching:
  - If path resolution or file I/O fails, current_state remains the initial message or default.
- Payload Construction:
  - worker_payload comprises:
    - task_context: includes File Target, Current State, and Goal
    - instruction: "Output raw text only. Do not use markdown blocks or explanations."
- Invocation:
  - role_description is looked up from self.config by tool_name.
  - raw_output_stream = self.connector.send_raw_request(worker_payload, system_prompt=role_description)
- Output:
  - The final return value is the concatenated and trimmed string from raw_output_stream.

## 6. Resource Dependencies
- **Standard Libraries**: 
  - os
  - typing (Any, Dict)
- **Internal Modules**: 
  - _resolve_path (from ai.tools.agent_tools) 
    - See [agent_tools](/docs/ai/tools/agent_tools.md) for the path-resolution utility.
- **External Packages**: 
  - None
