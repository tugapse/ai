## Module Purpose
This file implements the `OpenAIAPIModel` class, which provides a lazy-loading interface for interacting with the OpenAI API for chat completions, supporting both streaming and non-streaming modes.

## Interface & Exports
*   Class: `OpenAIAPIModel`

## Internal Logic
The `OpenAIAPIModel` class initializes by attempting to import the `openai` library lazily. It retrieves the OpenAI API key from either constructor arguments or the `OPENAI_API_KEY` environment variable. Default API call options like `temperature`, `max_tokens`, `top_p`, `presence_penalty`, and `frequency_penalty` are set. The `_convert_messages` method translates an internal message format to the OpenAI API's required structure, optionally including a system prompt. The `chat` method orchestrates API calls; if `stream` is `True`, it spawns a separate thread (`_run_streaming_chat`) to handle chunked responses and trigger "token" events; otherwise, it performs a synchronous completion call. The `_run_streaming_chat` method iterates through the streaming response, triggering "token" events for each content delta until a stop event is set or the stream concludes. A `clean_cache` method explicitly triggers garbage collection.

## Dependencies
*   `os`
*   `threading`
*   `gc`
*   `.base_llm` (for `BaseModel`)
*   `functions` (aliased as `func`)
*   `openai` (lazy imported `OpenAI` class)

## Constants & Environment
*   Environment Variable: `OPENAI_API_KEY`
*   Default `model_name`: `"gpt-4o"`
*   Default `temperature`: `0.5`
*   Default `max_tokens`: `2048` (derived from `max_new_tokens`)
*   Default `top_p`: `0.95`
*   Default `presence_penalty`: `0.0`
*   Default `frequency_penalty`: `0.0`
*   Event Identifier: `BaseModel.STREAMING_FINISHED_EVENT`
*   Event Identifier: `"token"`