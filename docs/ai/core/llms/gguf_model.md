## Module Purpose
This file defines the `GGUFImageLLM` class, which provides an interface for loading and interacting with GGUF (GGML Unified Format) language models, specifically designed for CPU inference. It includes functionality for chat completions, handling image inputs, and managing model generation in both streaming and synchronous modes, while also muting `llama_cpp`'s internal logging.

## Interface & Exports
*   `GGUFImageLLM`: A class inheriting from `BaseModel` that encapsulates the logic for loading and interacting with GGUF models.

## Internal Logic
The `GGUFImageLLM` class initializes by downloading a specified GGUF model from Hugging Face Hub and loading it into a `llama_cpp.Llama` instance, with `llama_cpp`'s logging globally muted. It supports `chat` functionality, which can operate in either a streaming or synchronous mode. For streaming, a dedicated thread (`_generate_in_thread`) is used to yield tokens via a queue, allowing for real-time output. Image inputs are processed by the inherited `load_images` method and appended to the user's prompt. The `check_system_prompt` method is also used to ensure the system prompt is correctly formatted. Model generation parameters like `max_new_tokens`, `temperature`, and `top_p` can be configured during initialization or overridden per chat call.

## Dependencies
*   `os`
*   `threading`
*   `queue`
*   `gc`
*   `ctypes`
*   `typing.List`
*   `typing.Dict`
*   `typing.Any`
*   `huggingface_hub.hf_hub_download`
*   `llama_cpp.Llama`
*   `llama_cpp.llama_log_set`
*   `core.llms.base_llm.BaseModel`
*   `core.llms.base_llm.ModelParams`
*   `functions` (internal module)
*   `color.Color` (internal module)

## Constants & Environment
*   `_null_log_callback`: A Python function used to silence `llama_cpp` logging.
*   `_log_callback_type`: A `ctypes.CFUNCTYPE` definition for the log callback.
*   `_callback_ref`: A `ctypes` reference to `_null_log_callback`.
*   `n_ctx`: Default context window size, hardcoded to `4000`.
*   `options`: Default model parameters, if `model_params` is not provided during initialization:
    *   `max_new_tokens`: `2048`
    *   `temperature`: `0.7`
*   `_generate_in_thread` and `chat` methods use default generation parameters if not provided in `gen_options` or `options`:
    *   `max_tokens`: `1024` (in `_generate_in_thread` and `chat` for `max_new_tokens`)
    *   `temperature`: `0.7`
    *   `top_p`: `0.95`
*   `BaseModel.STREAMING_FINISHED_EVENT`: An event triggered upon completion of streaming or synchronous generation.