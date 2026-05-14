## 1. Architectural Role

**Functional Mission**
The **SpecialistManager** is designed to orchestrate high-complexity, unstructured generation tasks by delegating specific tool-based requests to specialized LLM workers. Its primary mission is to act as a routing and context-enrichment layer that transforms a tool invocation into a highly focused prompt, ensuring that "specialist" models receive the necessary file state and specific role descriptions to perform precise writing or patching operations.

**System Context & Integration**
This component sits within the agentic orchestration layer, serving as a bridge between general tool execution and specialized model invocation. It consumes a `connector` (likely an implementation of an LLM interface) to dispatch raw requests. When a tool is identified as a specialist tool via `is_specialist_tool`, the manager intercepts the execution flow to perform file-system lookups via [agent_tools](/docs/tools/agent_tools.md), constructs a detailed task context including the current file state, and returns a raw text stream to the caller.

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `3000` (Default: `3000`)  The character limit for the `current_state` buffer when reading existing files to prevent context overflow.
- `"unknown"` (Default: `"unknown"`)  Fallback value for the `path` parameter if not provided.
- `"Complete task."` (Default: `"Complete task."`)  Fallback instruction if `instructions`, `content`, or `replace` keys are missing from parameters.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `SpecialistManager` | Class | Manages the lifecycle and invocation of specialist LLM workers. |
| `__init__` | Method | Initializes the manager with an LLM connector and a specialist configuration mapping. |
| `is_specialist_tool` | Method | Validates if a given `tool_name` exists within the provided specialist configuration. |
| `invoke` | Method | Orchestrates the context gathering (file reading), payload construction, and raw LLM request execution. |

## 4. Execution Logic & Flow
- **Initialization**: The class is instantiated with a `connector` object for LLM communication and a `specialist_config` dictionary that maps tool names to specific system prompts (role descriptions).
- **Data Path**: 
    1. **Input**: Receives `tool_name` and a `params` dictionary containing `instructions`/`content`/`replace` and `path`.
    2. **Context Retrieval**: Attempts to resolve the file `path` using `_resolve_path`. If the file exists, it reads the first 3000 characters to populate `current_state`.
    3. **Payload Construction**: Aggregates the target path, the current file content, and the goal into a `task_context` string. Adds a strict formatting instruction to the `instruction` field.
    4. **LLM Dispatch**: Sends the payload to the `connector.send_raw_request` using the tool's role description as the `system_prompt`.
    5. **Output**: Converts the resulting `raw_output_stream` into a single stripped string.
- **Conditional Branching**:
    - **Tool Validation**: `is_specialist_tool` checks for membership in `self.config`.
    - **File Existence**: The `try...except` block handles cases where the file path is invalid, inaccessible, or does not exist, defaulting `current_state` to a placeholder string.
    - **Parameter Fallback**: Uses logical `or` chains to select the most appropriate instruction key from the `params` dictionary.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `typing`
- **Internal Modules**: 
    - [agent_tools](/docs/tools/agent_tools.md)
- **External Packages**: None identified.