## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| SpecialistManager | [ai/agents/specialist_manager](/ai/agents/specialist_manager.md) |

This component is responsible for managing and executing specialized LLM workers when the task complexity demands unstructured generation, such as writing new code or modifying existing files. It acts as an orchestration layer, taking a high-level goal and contextualizing it with the current state of a target file before passing it to the appropriate specialized model.

It functions as a service layer within the application architecture, bridging the main task execution flow with specialized, powerful LLM agents. It relies on an injected `connector` to communicate with the models and uses the `specialist_config` to determine which specialist role description to apply for a given tool invocation.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| SpecialistManager | Class | Manages invocations of specialist LLM workers. |
| is_specialist_tool | Method | Checks if a given tool name is configured as a specialist tool. |
| invoke | Method | Invokes the specialist worker with a specific goal and parameters, returning the raw text output. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The `invoke` method first resolves the target path. It reads the content of the target file, truncating it to 3000 characters if the file exists, to build a `current_state`. It then constructs a payload combining the file target, the current state, and the user's goal. This payload, along with the specialist's role description, is sent to the connector.
- **Side Effects:** Reads from the filesystem (`os.path.exists`, `open`). Interacts with an external service via `self.connector.send_raw_request`.
- **Error Handling:** Catches generic exceptions during file reading/path resolution, falling back to a default "File does not exist yet or is empty" state if an error occurs.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `os`, `typing`
- **Internal:** [ai.tools.base](/ai/tools/base.md)