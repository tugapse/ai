## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| schemas | /ai/modules/server/schemas.md |

This component defines the strict data models (schemas) used for communication between the client and the AI server backend. It utilizes Pydantic to enforce data integrity, ensuring that incoming and outgoing data structures conform to expected types, constraints, and formats for chat interactions and prompt management.

It serves as the primary data contract layer for the server API. By defining these models, it dictates the expected input structure for functions like [ChatCompletionRequest](/ai/modules/server/schemas.md) and the output structure for data persistence layers, ensuring consistency across the application logic.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| ChatMessage | Class | Represents a single message within a chat conversation, including optional image data URLs. |
| ChatCompletionRequest | Class | Defines the full structure required to request a chat completion from the AI model, including session and sampling parameters. |
| UpdateSessionRequest | Class | Defines the structure used to update an existing chat session, allowing for title changes or full content replacement. |
| Prompt | Class | Represents metadata for a stored prompt file, tracking its filename and last update time. |
| PromptData | Class | Represents the complete data structure for a prompt, combining metadata with the actual text content. |
| PromptUpdateRequest | Class | Defines the structure for updating only the content of an existing prompt. |
| PromptCreateRequest | Class | Defines the structure for creating a new prompt file, specifying its path and initial content. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The `ChatMessage` model implements a custom field validator (`_check_images`) that performs several checks on image data URLs: ensuring the count does not exceed `MAX_IMAGES_PER_MESSAGE`, verifying the data URL format using a regex, and validating the size of the base64 encoded data against `MAX_IMAGE_BYTES`. Other models primarily serve as structured containers for request/response payloads.

- **Side Effects:** None. The code only defines data structures and validation logic; it does not perform I/O or network operations.

- **Error Handling:** The `ChatMessage` validator raises `ValueError` if the image count exceeds the limit, if the format is incorrect, or if the decoded size of any image exceeds the defined byte limit.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `re`, `pydantic`
- **Internal:** None