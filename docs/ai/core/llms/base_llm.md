## Module Purpose
This file defines a `BaseModel` class that serves as an abstract base for Large Language Models (LLMs), providing common functionalities such as initialization, input preparation, event handling, and resource management. It also includes a `ModelParams` class for standardizing model configuration parameters.

## Interface & Exports
*   `BaseModel`: A base class intended to be inherited by specific LLM implementations, providing shared attributes and methods for model management, input processing, and event handling.
*   `ModelParams`: A class for encapsulating and managing various configurable parameters for LLM inference, such as context window size, token generation limits, and sampling settings.

## Internal Logic
The `BaseModel` class initializes with a model name and optional system prompt, managing event listeners and generation interruption events (`stop_generation_event`, `_generation_thread`). It includes logic to detect PyTorch CUDA availability and set the `inference_device`. The `_prepare_input` method formats chat messages for model consumption, either by using a tokenizer's `apply_chat_template` or through manual string concatenation, ensuring the system prompt is correctly placed. It provides abstract methods (`chat`, `list`, `pull`) that subclasses must implement. The `clean_cache` method handles GPU memory cleanup. The `ModelParams` class internally stores various inference parameters and provides a `to_dict` method for easy conversion.

## Dependencies
*   `gc`
*   `threading`
*   `functions`
*   `entities.model_enums`
*   `torch` (conditionally imported within `init_pytorch_cuda` and `is_gpu_available`, `clean_cache`)

## Constants & Environment
*   `BaseModel.CONTEXT_WINDOW_SMALL`: `2048`
*   `BaseModel.CONTEXT_WINDOW_MEDIUM`: `4096`
*   `BaseModel.CONTEXT_WINDOW_LARGE`: `8192`
*   `BaseModel.CONTEXT_WINDOW_XLARGE`: `16384`
*   `BaseModel.CONTEXT_WINDOW_HUGE`: `32768`
*   `BaseModel.CONTEXT_WINDOW_GIANT`: `65536`
*   `BaseModel.STREAMING_FINISHED_EVENT`: `"streaming_finished"`
*   `ModelParams` default values:
    *   `num_ctx`: `BaseModel.CONTEXT_WINDOW_LARGE`
    *   `max_new_tokens`: `2048`
    *   `max_length`: `4096`
    *   `do_sample`: `True`
    *   `top_k`: `50`
    *   `top_p`: `0.95`
    *   `temperature`: `0.5`
    *   `quantization_bits`: `0`
    *   `enable_thinking`: `True`
    *   `presence_penalty`: `1.0`
    *   `frequency_penalty`: `1.0`
    *   `use_system_prompt`: `True`
    *   `inference_backend`: `InferenceBackend.CPU`