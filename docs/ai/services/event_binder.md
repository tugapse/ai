## Module Purpose
This file defines the `EventBinder` class, which is responsible for managing and binding event listeners to core `Chat` and LLM events within the application.

## Interface & Exports
*   `EventBinder` (class)
*   `EventBinder.bind_core_events` (static method)

## Internal Logic
The `EventBinder` class contains a static method `bind_core_events` that takes a `Chat` instance, a `BaseModel` (LLM) instance, and several `Callable` callback functions. This method registers the provided callbacks as listeners for specific events: `chat.EVENT_CHAT_SENT` and `chat.EVENT_OUTPUT_REQUESTED` on the `Chat` instance, and `BaseModel.STREAMING_FINISHED_EVENT` on the `BaseModel` instance if the `llm` object is provided.

## Dependencies
*   `core.llms.base_llm`
*   `core.chat`
*   `typing`

## Constants & Environment
None identified in source.