## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | SpecialistManager |
| Source file | specialist_manager.py |

The **SpecialistManager** serves as a specialized delegation layer designed to handle high-complexity, unstructured generation tasks that exceed the capabilities of standard agentic tool calls. It acts as a bridge between general-purpose agent logic and highly specialized LLM personas, specifically targeting tasks such as complex code writing or intricate file patching.

**Functional Mission**
The primary responsibility of the **SpecialistManager** is to orchestrate "specialist" LLM workers by providing them with deep context regarding the current state of a target file and a specific persona-driven instruction set. It solves the problem of "context dilution" by isolating complex generation tasks into a dedicated execution flow where the model is strictly instructed to act as a specialist and return raw, unformatted content.

**System Context & Integration**
This component functions as a high-level utility within the agentic workflow. It consumes a `connector` (typically an implementation of an LLM interface) to dispatch requests. When a tool is identified as a "specialist tool" via its configuration, the manager intercepts the execution to provide a rich `task_context` which includes the target file path and a truncated preview of the file's current content. This ensures the specialist worker has the necessary state to perform precise modifications. The output is then returned as a raw string, intended to be consumed by subsequent file-system or parsing modules.

- **INTERNAL REFERENCES**: The manager utilizes [agent_tools](/docs/ai/tools/agent_tools.md) for path resolution and relies on a `connector` which interfaces with the broader LLM orchestration layer.

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `3000` (Default: `3000`)  The maximum number of characters read from a target file to prevent context window overflow during state injection.
- `"unknown"` (Default: `"unknown"`)  Fallback value for the file path if not provided in parameters.
- `"Complete task."` (Default: `"Complete task."`)  Fallback instruction if no goal/content/replace parameters are found.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `SpecialistManager` | Class | Manages the lifecycle and invocation of specialist LLM workers. |
| `is_specialist_tool` | Method | Validates if a given `tool_name` exists within the provided specialist configuration. |
| `invoke` | Method | Executes the specialist workflow: resolves paths, reads file state, constructs a payload, and streams raw text from the connector. |

## 4. Execution Logic & Flow
- **Initialization**: The class is instantiated with a `connector` (for LLM communication) and a `specialist_config` (a mapping of tool names to specific system prompts/roles).
- **Data Path**: 
    1. **Input**: Receives `tool_name` and a `params` dictionary containing `instructions`/`content`/`replace` and `path`.
    2. **Context Gathering**: Attempts to resolve the `path` using `_resolve_path`. If the file exists, it reads the first 3000 characters to establish `current_state`.
    3. **Payload Construction**: Wraps the `current_state`, `path`, and `goal` into a `task_context` string. Adds a strict formatting instruction to the `instruction` field.
    4. **LLM Invocation**: Sends the payload to the `connector.send_raw_request` using the role description from the config as the `system_prompt`.
    5. **Output**: Aggregates the resulting stream into a single string and returns it stripped of leading/trailing whitespace.
- **Conditional Branching**:
    - **Tool Validation**: `is_specialist_tool` checks membership in `self.config`.
    - **Parameter Fallback**: Uses logical `or` chains to select the most relevant instruction parameter (`instructions` $\rightarrow$ `content` $\rightarrow$ `replace` $\rightarrow$ default).
    - **Error Handling**: A broad `try-except` block wraps the file reading logic; if path resolution or file reading fails, `current_state` defaults to a placeholder string rather than crashing the invocation.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `typing`
- **Internal Modules**: 
    - [agent_tools](/docs/ai/tools/agent_tools.md)
- **External Packages**: None identified.