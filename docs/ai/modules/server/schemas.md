## 1. Architectural Role
|  |  |
| :--- | :--- |
| Name | schemas.py |
| Source file | schemas.py |

The **schemas.py** component serves as the data contract layer for the server module. It utilizes Pydantic models to define the structural requirements for incoming API requests and outgoing data representations, ensuring strict type validation and data integrity across the network boundary.

**Functional Mission**
The primary responsibility of **schemas.py** is to provide a centralized, type-safe definition of the data structures used in chat completions, session management, and prompt manipulation. By enforcing these schemas, the component solves the problem of inconsistent data payloads and provides automatic validation for the server's API endpoints.

**System Context & Integration**
This component acts as the gatekeeper for the [Server Module](/docs/ai/modules/server/server_module.md). It is heavily utilized by the API routers, specifically [Prompts Router](/docs/ai/modules/server/routers/prompts.md) and [Sessions Router](/docs/ai/modules/server/routers/sessions.md), to parse and validate request bodies. The data validated by these schemas is subsequently passed to downstream services such as the [Chat Service](/docs/ai/modules/server/services/chat.md), [Prompt Manager](/docs/ai/modules/server/services/prompt_manager.md), and [Session Manager](/docs/ai/modules/server/services/session_manager.md) for business logic execution.

## 2. Environment & Configuration
**Environment Lookups:**
- No environment lookups identified.

**Hardcoded Constants:**
- `temperature` (Default: `0.7`)  Default sampling temperature for LLM completions within `ChatCompletionRequest`.

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ChatMessage` | Class | Represents a single message unit containing a `role` and `content`. |
| `ChatCompletionRequest` | Class | Defines the payload for initiating a chat session, including messages, model parameters, and session metadata. |
| `UpdateSessionRequest` | Class | Defines the payload for modifying existing session titles or contents. |
| `Prompt` | Class | Base schema for prompt metadata, tracking `filename` and `last_updated` timestamp. |
| `PromptData` | Class | Extends `Prompt` to include the actual string `content`. |
| `PromptUpdateRequest` | Class | Defines the payload for updating the text content of a prompt. |
| `PromptCreateRequest` | Class | Defines the payload for creating a new prompt via a file path and content. |

## 4. Execution Logic & Flow
- **Initialization**: Models are initialized via Pydantic's constructor, performing type checking and field validation against the provided input dictionary.
- **Data Path**: 
    1. **Input**: Raw JSON payload received via HTTP request.
    2. **Processing**: Pydantic parses the JSON, validates types (e.g., ensuring `messages` is a `List[ChatMessage]`), and applies default values (e.g., `stream=False`).
    3. **Output**: A validated Python object instance passed to the service layer.
- **Conditional Branching**: Validation logic triggers errors if required fields (like `role` in `ChatMessage`) are missing or if types are mismatched, preventing malformed data from reaching the core logic.

## 5. Resource Dependencies
- **Standard Libraries**: `typing`
- **Internal Modules**: 
    - No internal module imports identified.
- **External Packages**: 
    - `pydantic`