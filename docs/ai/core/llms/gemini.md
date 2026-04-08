## Module Purpose

This file defines the `GeminiAPIModel` class, which serves as an interface for interacting with Google's Gemini large language models, supporting both Vertex AI and Google GenAI SDKs for chat completions and multimodal capabilities.

## Interface & Exports

*   `class GeminiAPIModel(BaseModel)`: A class that provides methods for initializing, configuring, and interacting with Gemini models, including synchronous and streaming chat, and image handling.

## Internal Logic

The `GeminiAPIModel` class initializes by selecting between Vertex AI or Google GenAI SDK based on the `use_vertex` flag. It performs Google Cloud authentication checks for Vertex AI or requires an API key for GenAI. Message lists are converted into API-specific `Content` and `Part` objects, with image data loaded via `PIL.Image` and appended as `Part` objects. The `chat` method dispatches to either `_generate_response_sync` for single responses or `_stream_generator` for token-by-token output, both utilizing the respective SDKs' content generation methods and applying configured generation parameters. Token usage metadata is extracted and logged. It also includes methods `is_gpu_available` (always returning `False`) and `clean_cache`.

## Dependencies

*   `os`
*   `threading`
*   `io`
*   `gc`
*   `time`
*   `re`
*   `subprocess`
*   `warnings`
*   `.base_llm` (imports `BaseModel`, `ModelParams`)
*   `functions as func`
*   `color.Color`
*   `vertexai` (conditionally imported within `__init__`, `_convert_messages_to_api