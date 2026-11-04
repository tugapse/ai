## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **schemas** | [src/ai/modules/server/schemas.py](/src/ai/modules/server/schemas.py) |

This component defines the Pydantic data models used for request and response validation within the server module. It serves as the formal contract for API interactions, ensuring that incoming data for chat completions, session updates, and prompt management adheres to the expected structure and types.

The schemas are central to the server's communication layer, providing the data structures consumed by routers such as [src/ai/modules/server/routers/prompts.py](/AgentDocs/ai/modules/server/routers/prompts.md) and [src/ai/modules/server/routers/sessions.py](/AgentDocs/ai/modules/server/routers/sessions.md). By centralizing these definitions, the system maintains consistency between the client requests and the internal services like [src/ai/modules/server/services/chat.py](/AgentDocs/ai/modules/server/services/chat.md) and [src/ai/modules/server/services/prompt_manager.py](/AgentDocs/ai/modules/server/services/prompt_manager.md).

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `ChatMessage` | Class | Represents a single message in a conversation, containing `role` and `content`. |
| `ChatCompletionRequest` | Class | The primary request model for generating AI responses, including message history, model configuration, and session metadata. |
| `UpdateSessionRequest` | Class | Model used to modify an existing session's title or append/replace its message content. |
| `Prompt` | Class | Base metadata model for a stored prompt, containing `filename` and `last_updated` timestamp. |
| `PromptData` | Class | An extension of `Prompt` that includes the actual string `content` of the prompt. |
| `PromptUpdateRequest` | Class | Model for updating the text content of an existing prompt. |
| `PromptCreateRequest` | Class | Model used to initialize a new prompt file with a specific path and content. |

## 3. Implementation Details & Side Effects
Structural definitions only; no complex logic or side effects. The file utilizes Pydantic's `BaseModel` to enforce type validation and provide automatic serialization/deserialization for API payloads.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `pydantic`, `typing`
- **Internal:** No internal module imports detected.