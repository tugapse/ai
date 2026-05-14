## 1. Architectural Role
Defines the structural data contracts and validation schemas for API requests and responses related to chat completions, session management, and prompt manipulation.

## 2. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| `ChatMessage` | Class | Represents a single unit of dialogue containing a role and text content. |
| `ChatCompletionRequest` | Class | Defines the payload for initiating a chat interaction, including messages, model parameters, and session metadata. |
| `UpdateSessionRequest` | Class | Defines the payload for modifying existing session attributes like titles or message history. |
| `Prompt` | Class | Represents the metadata for a prompt file, tracking its location and modification timestamp. |
| `PromptData` | Class | Extends `Prompt` to include the actual string content of the prompt. |
| `PromptUpdateRequest` | Class | Defines the payload for modifying the text content of an existing prompt. |
| `PromptCreateRequest` | Class | Defines the payload required to initialize a new prompt file with a specific path and content. |

## 3. Execution Logic & Flow
- **Initialization**: No runtime logic; the module defines static data structures via `pydantic.BaseModel` inheritance.
- **Data Path**: Input (Raw Dictionary/JSON) $\rightarrow$ Pydantic Validation $\rightarrow$ Typed Class Instance.
- **Conditional Branching**: None; logic is strictly limited to type enforcement and schema definition.

## 4. Resource Dependencies
- **Standard Libraries**: `typing` (`List`, `Optional`, `Dict`, `Any`)
- **Internal Modules**: None
- **External Packages**: `pydantic` (Note: Code contains a typo `pydantic` as `pydantic` in import, but refers to `BaseModel`)

## 5. Configuration & Environment
- **Hardcoded Constants**: 
    - `ChatCompletionRequest.stream`: `False`
    - `ChatCompletionRequest.temperature`: `0.7`
- **Environment Lookups**: None