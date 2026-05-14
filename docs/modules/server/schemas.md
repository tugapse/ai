## 1. Architectural Role
This file serves as the structural definition layer for the server's communication protocols, utilizing Pydantic models to enforce strict type validation for incoming API requests and outgoing data structures. It defines the data contracts for chat completions, session management, and prompt orchestration, ensuring that the [modules/server/server_module.md](modules/server/server_module.md) and associated services like [modules/server/services/prompt_manager.md](modules/server/services/prompt_manager.md) and [modules/server/services/session_manager.md](modules/server/services/session_manager.md) operate on predictable, validated schemas.

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `temperature` (Default: `0.7`)  Default sampling randomness for LLM completions.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ChatMessage` | Class | Represents a single unit of dialogue containing a `role` and `content`. |
| `ChatCompletionRequest` | Class | Schema for LLM interaction, including message history, model parameters, and session metadata. |
| `UpdateSessionRequest` | Class | Schema for modifying existing session metadata or history. |
| `Prompt` | Class | Base metadata for a prompt file, tracking `filename` and `last_updated` timestamp. |
| `PromptData` | Class | Extended prompt schema including the actual string `content`. |
| `PromptUpdateRequest` | Class | Schema for submitting new content for an existing prompt. |
| `PromptCreateRequest` | Class | Schema for initializing a new prompt via a file path. |

## 4. Execution Logic & Flow
- **Initialization**: Models are instantiated as Pydantic objects, validating that input types match the specified type hints (e.g., ensuring `messages` is a `List` of `ChatMessage`).
- **Data Path**: 
    - **Input**: Raw JSON payload from a network request.
    - **Processing**: Pydantic parsing/coercion (e.g., converting a string to a float for `temperature` or a float to a timestamp for `last_updated`).
    - **Output**: A validated Python object instance used by downstream services.
- **Conditional Branching**: 
    - `Optional` fields allow for partial payloads (e.g., `system_prompt` or `stream` may be omitted, defaulting to `None` or `False` respectively).

## 5. Resource Dependencies
- **Standard Libraries**: `typing`
- **Internal Modules**: 
    - None.
- **External Packages**: `pydantic` (Note: Code references `pydantic` as `pydantic` despite a likely typo `pydantic` in the source import `pydantic` vs `pydantic`).