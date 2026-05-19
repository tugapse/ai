## 1. Architectural Role
| Name | Source file |
| :--- | :--- |
| Agent | [src/ai/agents/agent.py](/src/ai/agents/agent.py) |

The **Agent** component serves as the high-level facade that encapsulates the complete agentic loop. It coordinates the loading of the pipeline configuration, construction of core subsystems (a tool registry, LLM connector, and message orchestrator), and exposure of a run interface to execute the agents behavior against user prompts. On initialization, the component loads the pipeline, wires together the core components, and subscribes to event propagation so that downstream orchestrator events bubble up to the agent level.

During runtime, **Agent** manages session lifecycle and delegates the turn-by-turn execution to the orchestrator. It handles session creation when none is provided, triggers lifecycle events before and after LLM requests, and delegates the actual prompting and response handling to the orchestrator. This placement makes it the central integration point between configuration, core execution engines, and the external user interaction loop, ensuring a cohesive flow from input prompt through to LLM-driven action.

- Internal cross-links:
  - [ToolRegistry](/docs/ai/tools/tool_registry.md)
  - [LLMConnector](/docs/ai/agents/llm_connector.md)
  - [MessageOrchestrator](/docs/ai/agents/message_orchestrator.md)
  - [Events](/docs/ai/core/events.md)
  - [Functions](/docs/ai/functions.md)
  - [ProgramSetting](/docs/ai/config.md)

## 2. Environment & Configuration
**Environment Lookups:**
- ROOT_DIRECTORY (via prog.config.get(ProgramSetting.ROOT_DIRECTORY))  Used to locate the pipelines and prompt files relative to the project root.

  [ProgramSetting](/docs/ai/config.md)

**Hardcoded Constants:**
- No hardcoded constants identified.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| load_pipeline_config | Function | Loads and validates the pipeline configuration JSON, resolves prompt files, and returns the parsed config or empty on failure. |
| Agent | Class | High-level facade that initializes core components, wires event propagation, and runs the agent loop for a given user prompt and session. |

## 4. Code Example
```python
# Example usage (assuming a properly configured `prog` object)
from ai.agents.agent import Agent

# prog should provide .config, .llm, and .modules as expected by Agent
agent = Agent(prog, "default.json")
agent.run("Describe the current system status.")
```

## 5. Execution Logic & Flow
- Initialization
  - In __init__, Agent loads the pipeline config via load_pipeline_config(prog, pipeline_file).
  - Constructs core components: ToolRegistry, LLMConnector, and MessageOrchestrator.
  - Connects orchestrator events to propagate to the Agent level (BEFORE/AFTER LLM REQUEST).

- Data Path
  - run(user_prompt, session_id) is invoked to start processing.
  - If session_id is empty, a new session UUID is created, and a log is emitted.
  - Delegates to self.orchestrator.run_loop(user_prompt, session_id) to drive the agents loop.

- Conditional Branching
  - If load_pipeline_config fails (returns empty), Agent.__init__ raises ValueError.
  - In load_pipeline_config, missing pipeline or prompt files trigger func.error and return {} to signal failure.

## 6. Resource Dependencies
- **Standard Libraries**: os, sys, json, uuid
- **Internal Modules**: 
  - [ToolRegistry](/docs/ai/tools/tool_registry.md)
  - [LLMConnector](/docs/ai/agents/llm_connector.md)
  - [MessageOrchestrator](/docs/ai/agents/message_orchestrator.md)
  - [Events](/docs/ai/core/events.md)
  - [Functions](/docs/ai/functions.md)
  - [ProgramSetting](/docs/ai/config.md)
- **External Packages**: None

