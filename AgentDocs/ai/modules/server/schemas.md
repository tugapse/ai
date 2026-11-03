## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| **schemas** | [src/ai/modules/server/schemas.py](/AgentDocs/ai/modules/server/schemas.py) |

This component defines the Pydantic data models used for request and response validation within the server module. It serves as the formal contract for API communication, ensuring that incoming data for chat completions, session updates, and prompt management adheres to strict structural requirements.

The schemas are primarily utilized by the server's routing and service layers to deserialize JSON payloads into typed Python objects. By centralizing these definitions, the component provides a single source of truth for the data structures governing chat history, session metadata, and prompt configuration across the server architecture.

## 2. Public API & Interfaces

| Entity | Type | Description |
| :--- | :--- | :--- |
| `ChatMessage` | Class | Represents a single message in a conversation, containing a `role` (e.g., 'user', 'assistant') and `content`. |
| `ChatCompletionRequest` | Class | Defines the payload for generating AI responses, including message history, model selection, system prompts, and session identifiers. |
| `UpdateSessionRequest` | Class | Defines the payload for modifying an existing session, such as updating its title or appending new messages. |
| `Prompt` | Class | A base metadata model for stored prompts, containing a `filename` and a `last_updated` timestamp. |
| `PromptData` | Class | An extension of `Prompt` that includes the full string `content` of the prompt. |
| `PromptUpdateRequest` | Class | Defines the payload for updating the text content of an existing prompt. |
| `PromptCreateRequest` | Class | Defines the payload for creating a new prompt, requiring a `prompt_path` and initial `content`. |

## 3. Implementation Details & Side Effects
Structural definitions only; no complex logic or side effects. The file relies on Pydantic's validation engine to enforce type constraints and default values (e.g., `temperature` defaulting to `0.7` and `stream` defaulting to `False`) during object instantiation.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `pydantic`, `typing`
- **Internal:** No internal module imports detected.