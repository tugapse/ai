## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| AgentIO | ai/agents/agent_io.md |

This component provides a standardized Input/Output (I/O) abstraction layer for the agent orchestrator, decoupling the core logic from specific interaction mechanisms like a terminal or a chat UI. Its primary responsibility is to define the contract for how the orchestrator communicates events to an external system and how it requests necessary inputs (permissions or user answers) from that system.

This layer serves as a crucial interface component within the application architecture. It abstracts away the rendering logic, allowing the orchestrator to emit generic `AgentEvent` objects. Concrete implementations, such as [ConsoleIO](/ai/agents/agent_io.md), handle the specific translation of these events into terminal output, while other specialized I/O classes would handle different environments like a chat interface.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| AgentEventType | Enum | Defines the standardized kinds of events the orchestrator can emit (e.g., `HEADER`, `MESSAGE`, `QUESTION`). |
| AgentEvent | Class | A data structure encapsulating a single event, containing its type, agent context, text content, and arbitrary data payload. |
| AgentIO | Class | The abstract base class defining the contract for all I/O implementations, including methods for emitting events and requesting user interaction. |
| ConsoleIO | Class | A concrete implementation of `AgentIO` that specifically handles rendering events to the classic terminal interface using `TerminalUI`. |

## 3. Implementation Details & Side Effects
- **Core Logic:** `ConsoleIO` implements event dispatching by routing `AgentEvent` types to specific methods within the imported [TerminalUI](/ai/agents/terminal_ui.md). It manages interactive loops by blocking on `input()` for permissions and user prompts when `blocking_user_input` is true.
- **Side Effects:** Interacts heavily with standard input/output (`input()`, `func.out()`, `func.error()`), and relies on the state management provided by [TerminalUI](/ai/agents/terminal_ui.md) to display information to the console.
- **Error Handling:** Catches operational errors by emitting `AgentEventType.ERROR`, which `ConsoleIO` translates into a call to `func.error()`.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `dataclasses`, `enum`, `typing`
- **Internal:** [ai.functions](/ai/functions.md), [ai.color](/ai/color.md), [ai.agents.terminal_ui](/ai/agents/terminal_ui.md)