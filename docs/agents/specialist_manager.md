## 1. Architectural Role
The `SpecialistManager` class acts as a high-complexity task delegator within the agentic framework, specifically designed to offload unstructured generation tasks (such as file writing or patching) to specialized LLM workers. It abstracts the process of context assemblycombining file state, target paths, and specific instructionsand orchestrates a raw text stream via a provided connector to ensure high-fidelity output without markdown interference. It relies on [tools/agent_tools.md](tools/agent_tools.md) for path resolution and expects a specialized configuration to map tool names to expert roles.

## 2. Environment & Configuration
**Environment Lookups:**
- `specialist_config` (via `__init__`)  A dictionary mapping specific tool identifiers to their corresponding specialist role descriptions.

**Hardcoded Constants:**
- `3000` (Default: `3000`)  The character limit for the `current_state` file snippet to prevent context window overflow.
- `"unknown"` (Default: `"unknown"`)  Fallback string for the `path` parameter if not provided in `params`.
- `"Complete task."` (Default: `"Complete task."`)  Fallback instruction if no goal-oriented keys are found in `params`.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `SpecialistManager` | Class | Orchestrates specialized LLM calls for complex content generation. |
| `__init__` | Method | Initializes the manager with an LLM connector and tool-to-role configuration. |
| `is_specialist_tool` | Method | Validates if a given tool name has an associated specialist configuration. |
| `invoke` | Method | Performs the end-to-end workflow of context gathering, payload construction, and specialist execution. |

## 4. Execution Logic & Flow
- **Initialization**: Sets the `connector` (used for LLM communication) and `config` (mapping of tools to roles) as instance attributes.
- **Data Path**:
    1. **Input**: Receives `tool_name` and a `params` dictionary (containing `instructions`/`content`/`replace` and `path`).
    2. **Context Assembly**: 
        - Attempts to resolve the target `path` via `_resolve_path`.
        - Reads up to 3000 characters of the existing file to establish `current_state`.
        - Constructs a `worker_payload` containing the file target, current state, and the goal.
    3. **Processing**: Dispatches the payload and the role-specific system prompt to `self.connector.send_raw_request`.
    4. **Output**: Aggregates the resulting `raw_output_stream` into a single string and returns the stripped text.
- **Conditional Branching**:
    - `is_specialist_tool` checks for existence of `tool_name` in `self.config`.
    - `params.get(...)` chain implements a priority ladder for determining the primary task instruction.
    - `os.path.exists` determines whether to attempt reading file content for context or to use a default empty state message.

## 5. Resource Dependencies
- **Standard Libraries**: `os`, `typing`
- **Internal Modules**: 
    - [tools/agent_tools.md](tools/agent_tools.md)
- **External Packages**: None identified.