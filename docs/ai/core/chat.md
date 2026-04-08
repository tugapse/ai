## Module Purpose
This file defines the `ChatRoles` class for standardizing chat participant roles and the `Chat` class, which manages the interactive chat session, processes user input, handles chat history, and triggers events related to chat activities.

## Interface & Exports
*   `ChatRoles` (class): Defines constants for different user roles in a chat.
*   `Chat` (class): Manages the chat session, including input/output, message history, command handling, and event triggering.

## Internal Logic
The `Chat` class extends `Events` to manage a chat loop, user input, and message history. It uses `PromptSession` for interactive input, supporting both single-line and multiline messages. User input is checked for termination tokens or commands (e.g., `/clear`, `/agent`). Valid chat messages are added to an internal `messages` list, which is capped at `max_chat_log`. The class manages state flags like `running_command` and `waiting_for_response` to control when user input is prompted. It triggers various events (`EVENT_CHAT_SENT`, `EVENT_COMMAND_STARTED`, etc.) to communicate chat state changes and actions.

## Dependencies
*   `os`
*   `json`
*   `datetime`
*   `core.events.Events`
*   `color.Color`
*   `color.format_text`
*   `functions as func`
*   `core.llms.base_llm.BaseModel`
*   `prompt_toolkit.PromptSession`
*   `prompt_toolkit.history.InMemoryHistory`
*   `prompt_toolkit.formatted_text.ANSI`

## Constants & Environment
*   `ChatRoles.USER`: "user"
*   `ChatRoles.ASSISTANT`: "assistant"
*   `ChatRoles.SYSTEM`: "system"
*   `ChatRoles.CONTROL`: "control"
*   `ChatRoles.TOOL`: "tool"
*   `Chat.EVENT_CHAT_SENT`: "chat_sent"
*   `Chat.EVENT_COMMAND_STARTED`: "command_started"
*   `Chat.EVENT_OUTPUT_REQUESTED`: "output_requested"
*   `Chat.EVENT_MESSAGES_UPDATED`: "messages_updated"
*   `Chat.EVENT_AGENT_RUN_REQUESTED`: "agent_run_requested"
*   `self.terminate_tokens`: `["quit", "q"]`
*   `self.user_prompt`: "User: "
*   `self.assistant_prompt`: "Assistant: "
*   `self.max_chat_log`: 50
*   `self.cache_messages`: `True`