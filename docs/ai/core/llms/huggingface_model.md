## Module Purpose
This file defines the `HuggingFaceModel` class, which integrates Hugging Face models as a Large Language Model (LLM) backend, handling model loading, optional quantization, and streaming response generation. It also includes a custom stopping mechanism for generation.

## Interface & Exports
*   `class CustomStoppingCriteria`: A class designed to allow external interruption of model generation via