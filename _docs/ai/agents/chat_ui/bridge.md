## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| ChatIO | /ai/agents/chat_ui/bridge.md |

This component serves as the critical thread bridge between the asynchronous orchestration logic (the worker thread) and the synchronous/asynchronous chat UI loop. Its primary responsibility is to manage the communication flow, ensuring that state changes, output messages, and permission requests are correctly routed between the two disparate execution contexts.

Architecturally, `ChatIO` acts as an Adapter or Facade layer. It wraps the shared `LiveState` to manage mutations, uses a provided `write` function to print committed output, and interfaces with the UI loop via `permission_handler` to block the worker thread safely during user interactions or permission checks.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| ChatIO | Class | Implements `AgentIO`, managing the bridge between worker and UI threads. |
| emit | Method | Processes an `AgentEvent`, updating `LiveState` based on the event type and printing the rendered output. |
| on_token | Method | Handles per-token callbacks from the LLM connector, updating token counts and triggering a UI redraw. |
| request_permission | Method | Synchronously requests user permission for a tool call by running the UI handler in the event loop and blocking the worker thread until a result is received. |
| request_user_input | Method | A placeholder method designed to handle blocking user input (currently disabled). |

## 3. Implementation Details & Side Effects
- **Core Logic:** The `emit` method contains the core state transition logic, routing specific `AgentEventType`s (like `STATUS`, `LLM_REQUEST`, `TOOL_CALL`) to mutate the `LiveState` accordingly. Permission requests utilize `asyncio.run_coroutine_threadsafe` to safely execute UI coroutines from the worker thread, blocking the worker until the future resolves.
- **Side Effects:** Interacts heavily with external state mutation (`self.state.invalidate()`), prints output to `sys.stdout` via the `self.write` callable, and blocks the worker thread during permission requests.
- **Error Handling:** In `request_permission`, exceptions during the future resolution are caught, causing the request to fail gracefully by returning `PERMISSION_NO`.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `asyncio`, `concurrent.futures`, `sys`, `time`, `typing`
- **Internal:** [ai.agents.agent_io.AgentEvent](/ai/agents/agent_io.md), [ai.agents.agent_io.AgentEventType](/ai/agents/agent_io.md), [ai.agents.agent_io.AgentIO](/ai/agents/agent_io.md), [ai.agents.chat_ui.renderer.LiveState](/ai/agents/chat_ui/renderer.md), [ai.agents.chat_ui.renderer.render_event](/ai/agents/chat_ui/renderer.md), [ai.agents.chat_ui.renderer.render_status_line](/ai/agents/chat_ui/renderer.md)