## 1. Architectural Role
| Name | Source file |
| :--- | :--- |
| **Chat** | [src/ai/chat/chat.py](/src/ai/chat/chat.py) |

The **Chat** module defines the central interactive Chat mechanism that drives user conversations, command handling, and agent/task orchestration. 

It encapsulates the lifecycle of a chat session, including prompt rendering, multiline input toggling, deferred file attachments, command execution, and agent-mode task capture. As the integration hub for user interactions and downstream processing, this component coordinates message queuing, event firing, and state transitions (e.g., ready, processing, agent-mode, and terminated). Its design enables modular extension via commands, agents, and attachment handling, serving as the primary entrypoint for chat-driven workflows within the system.

Chat orchestrates flow between user input, message construction, and downstream processing (e.g., agent tasks, chat output). It interacts with the broader execution pipeline by emitting events (EVENT_CHAT_SENT, EVENT_COMMAND_STARTED, EVENT_OUTPUT_REQUESTED, EVENT_MESSAGES_UPDATED, EVENT_AGENT_RUN_REQUESTED) that downstream services, modules, or orchestrators consume. 

It also collaborates with the colorized UI layer (via format_text and ANSI), the local prompt session (PromptSession with InMemoryHistory), and the BaseModel-based message formatting for chat history. This placement ensures consistent state handling, extensibility for new commands or agents, and clean separation between input parsing, attachment management, and output rendering.

Internal cross-links reference: [Events](/docs/ai/core/events.md), [BaseModel](/docs/ai/core/llms/base_llm.md), [Color](/docs/ai/color.md)

## 2. Environment & Configuration
**Environment Lookups:**
No environment lookups identified.

**Hardcoded Constants:**

| Name | Description |
| :--- | :--- |
| `max_chat_log` | Maximum number of messages retained in the chat log before trimming (Default: 50). |
| `terminate_tokens` | Tokens recognized to terminate the chat session (Default: `["quit", "q"]`). |
| (Other constants are implemented as instance attributes, not module-level constants.) | |

## 3. Interface & API Surface
| Entity | Type | Functional Responsibility |
| :--- | :--- | :--- |
| Chat | Class | Central interactive chat controller; handles input collection, command processing, multiline toggling, file attachments, agent/task capture, and event emission to downstream systems. |
| PrefixCompleter | Class | Lightweight completer for command and file path suggestions; supports slash-prefixed commands and at-sign file-path completions with directory browsing semantics. |
| ChatRoles | Class | Defines role constants used to classify message origins (USER, ASSISTANT, SYSTEM, CONTROL, TOOL). |

## 4. Code Example

- Basic usage (interactive execution):
```python
from ai.chat.chat import Chat
chat = Chat(commands=['/clear', '/agent'], agents=['agent1'])
chat.loop()  # starts the interactive loop (blocks awaiting input)
```

- Quick programmatic usage (non-interactive example):
```python
from ai.chat.chat import Chat
chat = Chat(commands=['/clear'], agents=[])
chat.send_chat("Hello, how can I assist you today?")
```

Note: The actual runtime requires the surrounding application/runtime environment and prompt-toolkit event loop.

## 5. Execution Logic & Flow
1) Initialization
- Chat.__init__ sets termination state, command/agent lists, message queues, prompts, input session (PromptSession), key bindings, and the completion engine (PrefixCompleter). It initializes deferred attachment storage (pending_files) and top-bar UI state.

2) Data Path
- Main loop (loop  process_loop_frame) awaits user input via PromptSession.prompt with:
  - Multiline support toggled by Escape+Enter
  - Dynamic bottom toolbar and prompt text rendering
  - Completions via PrefixCompleter
- After input, it clears residual line content, strips input, and handles:
  - File attachment syntax: inputs starting with '@' are deferred for attachment.
  - Agent mode: if agent_mode_active, collects the task alongside any pending files, emits EVENT_AGENT_RUN_REQUESTED, and clears pending files.
  - Commands: inputs starting with '/' are routed to run_command.
  - Regular messages: attachments (if any) are prepended to the message, then sent via send_chat; pending files are cleared.

3) Conditional Branching
- If agent mode is active, the input is treated as a task, combined with pending files, and dispatched as an agent run request.
- If input starts with '/', a command path is executed (e.g., /clear clears chat; /agent toggles agent mode).
- If neither, the input is treated as a user message; any pending file attachments are prepended to the message before sending.
- State flags (waiting_for_response, running_command, multiline_mode) steer UI prompts and bottom toolbars and gate behavior.

4) State Transitions
- send_chat marks waiting_for_response, stores the user message in history, and emits EVENT_CHAT_SENT.
- chat_finished finalizes the assistant reply into history and resets current_message.
- terminate_chat and terminate_command adjust termination or command execution states accordingly.

5) Output & Events
- The component emits events (EVENT_CHAT_SENT, EVENT_COMMAND_STARTED, EVENT_OUTPUT_REQUESTED, EVENT_MESSAGES_UPDATED, EVENT_AGENT_RUN_REQUESTED) to integrate with downstream services such as agents, memory, or server components.

## 6. Resource Dependencies
- Standard Libraries: os, datetime, typing.Optional
- Internal Modules:
  - [functions](/docs/ai/functions.md) (aliased as func)
  - [Events](/docs/ai/core/events.md) (Events)
  - [Color](/docs/ai/color.md) (Color, format_text)
  - [BaseModel](/docs/ai/core/llms/base_llm.md) (BaseModel)
- External Packages:
  - prompt_toolkit (PromptSession, InMemoryHistory, ANSI, KeyBindings, Condition, Completer, Completion)
- Notes on manifest-guided cross-links:
  - [Events](/docs/ai/core/events.md)
  - [Color](/docs/ai/color.md)
  - [BaseModel](/docs/ai/core/llms/base_llm.md)
  - [functions](/docs/ai/functions.md)
