## 1. Overview & Purpose
| Component | Source File |
| :--- | :--- |
| AgentChatApp | /ai/agents/chat_ui/app.md |

This component provides the core logic for the interactive, multi-turn chat interface built on `prompt_toolkit`. Its primary responsibility is managing the user experience, orchestrating the flow between user input, the agent's thinking process, and the display of results in a non-full-screen terminal layout. It handles command parsing, input validation, and user interaction states like permission prompts.

Architecturally, `AgentChatApp` acts as the main controller for the UI layer. It initializes and coordinates the `ChatIO` interface, the `orchestrator` (which relies on configurations like those found in [default.json](/ai/agents/chat_ui/default.json.md)), and the `TextArea` input widget. It bridges the asynchronous, daemon-threaded agent execution with the synchronous event loop of the `prompt_toolkit` application.

## 2. Public API & Interfaces
| Entity | Type | Description |
| :--- | :--- | :--- |
| `AgentChatApp` | Class | Manages the entire chat session lifecycle, including initialization, running the application loop, and handling user interactions. |
| `AgentChatCompleter` | Class | A `prompt_toolkit.completion.Completer` that allows users to trigger predefined commands using `/` and mention files using `@`. |
| `expand_mentions` | Function | Scans input text for `@path` patterns, reads the content of existing files, and appends the content to the message string. |
| `run_agent_chat` | Function | The CLI entry point function that instantiates and runs the `AgentChatApp` for command-line invocation. |

## 3. Implementation Details & Side Effects
- **Core Logic:** The application operates by managing several concurrent states: the main UI thread running the `prompt_toolkit` event loop, and a background `threading.Thread` (`self.worker`) running the agent's processing loop via `orchestrator.run_loop`. User input triggers state transitions (e.g., `submit` calls `_start_turn`), which launches the worker thread. The UI updates are managed by calling `self.invalidate()`, which forces a redraw based on the current state (`self.state`).
- **Side Effects:** The code heavily interacts with the filesystem via `expand_mentions` (reading files) and `_make_history` (creating/reading history files). It interacts with external state via `self.state` (managed by [R.LiveState](/ai/agents/chat_ui/renderer.md)) and the network/external services via the `orchestrator`.
- **Error Handling:** Catches exceptions during the agent turn (`_run_turn`) and reports them to the user via `self.write` using red formatting. It handles interruptions (`interrupt`) by detaching the worker thread and discarding its result, ensuring the UI remains responsive.

## 4. Dependencies & Configuration
**Environment & Configuration:**
No environment variables or external configurations required.

**Module Dependencies:**
- **Standard/External:** `asyncio`, `threading`, `time`, `uuid`, `re`, `os`.
- **Internal:** [ai.functions](/ai/functions.md), [ai.agents.agent_io](/ai/agents/agent_io.md), [ai.agents.chat_ui.bridge](/ai/agents/chat_ui/bridge.md), [ai.agents.chat_ui.renderer](/ai/agents/chat_ui/renderer.md), [ai.agents.chat_ui.commands](/ai/agents/chat_ui/commands.md), [ai.chat.chat](/ai/chat/chat.md), [ai.services.directory_manager](/ai/services/directory_manager.md).