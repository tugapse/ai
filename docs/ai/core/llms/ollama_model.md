## Module Purpose
This file implements the `OllamaModel` class, which provides an interface for interacting with Large Language Models via the Ollama library, supporting chat, model listing, and model pulling functionalities.

## Interface & Exports
- `OllamaModel`: A class that extends `BaseModel` to provide an LLM bot implementation using Ollama.

## Internal Logic
The `OllamaModel` class initializes an `ollama.Client` instance, optionally connecting to a specified host. Upon instantiation, it attempts to pull the specified model if it's not already present locally, displaying progress using `tqdm`. The `chat` method handles both streaming and non-streaming interactions, processing messages, optional image inputs, and model generation options. It includes error handling for generation and a mechanism to interrupt streaming generation via a `stop_generation_event`. The `pull` method checks for model existence and calls a private `__pull_model` method to download the model, showing a progress bar for each layer. The `join_generation_thread` method is a placeholder, as Ollama's streaming is synchronous and does not use a separate thread for generation.

## Dependencies
- `ollama`
- `tqdm`
- `sys`
- `threading`
- `core.events`
- `core.llms.base_llm` (imported as `.base_llm`)
- `functions`

## Constants & Environment
- `self.server_ip`: Defaults to `"127.0.0.1"` if no host is provided during initialization.
- Model tag default: When pulling a model, if no tag is specified (e.g., `model_name` is "llama2"), `":latest"` is appended to the model name.