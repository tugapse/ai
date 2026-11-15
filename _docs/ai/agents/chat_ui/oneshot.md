## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| OneShotIO | ai/agents/chat_ui/oneshot |

This component provides a specialized implementation of `ChatIO` designed for one-shot agent runs. Its primary responsibility is to direct all agent output straight to standard output (`stdout`) while managing user interactions, such as permission requests, using blocking input. It ensures that the entire agent run completes in a single invocation, unlike interactive sessions.

Architecturally, `OneShotIO` serves as the I/O bridge for non-interactive or script-driven execution paths. It wraps the core rendering logic from [ai/agents/chat_ui/renderer](/ai/agents/chat_ui/renderer.md) and manages the flow state, particularly when the agent needs user input (like permission checks) or signals it is done, which is crucial for the [ai/agents/chat_ui/bridge/ChatIO](/ai/agents/chat_ui/bridge/ChatIO.md) contract.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| OneShotIO | Class | Manages I/O for one-shot runs, handling terminal detection and permission prompts. |
| _prompt_preview | Function | Shortens a given prompt string for display at the start of the run, truncating long templates. |
| run_one_shot | Function | Executes a single agent request to completion using the chat UI renderer and returns the final `RunResult`. |

## 3. Implementation Details & Side Effects
- **Core Logic:** `OneShotIO` initializes based on whether `stdout` is a TTY to determine color support and interactivity. The `request_permission` method reads a single line from the user via `self.read()` and returns one of the defined `PERMISSION_*` constants based on the input. `run_one_shot` initializes the orchestrator, renders the initial prompt, runs the loop, and handles the final state summary, including printing a `--resume` hint if the run ended awaiting user input.

- **Side Effects:** Reads from `stdin` (via `self.read`) for permission prompts and writes to `stdout` (via `self.out`) for all agent output, status lines, and hints.

- **Error Handling:** Catches `EOFError` and `KeyboardInterrupt` during permission requests, defaulting the result to `PERMISSION_NO`. The `run_one_shot` function handles the final state by checking the `reason` returned by the orchestrator.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `re`, `sys`, `typing`, `uuid`.
- **Internal:** [ai/agents/agent_io/PERMISSION_ALWAYS](/ai/agents/agent_io/PERMISSION_ALWAYS.md), [ai/agents/agent_io/PERMISSION_NO](/ai/agents/agent_io/PERMISSION_NO.md), [ai/agents/agent_io/PERMISSION_YES](/ai/agents/agent_io/PERMISSION_YES.md), [ai/agents/chat_ui/renderer/renderer](/ai/agents/chat_ui/renderer.md), [ai/agents/chat_ui/bridge/ChatIO](/ai/agents/chat_ui/bridge/ChatIO.md), [ai/agents/agent/build_orchestrator](/ai/agents/agent/build_orchestrator.md).