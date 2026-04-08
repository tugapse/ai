## Module Purpose
This file defines the `T5Model` class, which integrates T5-type (encoder-decoder / Seq2Seq) Hugging Face models for tasks like summarization or translation, processing the full conversation context as a single input.

## Interface & Exports
*   `T5Model` (class)

## Internal Logic
The `T5Model` class extends `BaseModel` and handles the loading and inference of T5-type models. During initialization, it attempts to load the specified Hugging Face model and tokenizer, supporting optional 4-bit or 8-bit quantization via `BitsAndBytesConfig` if `bitsandbytes` is available and a GPU is detected. It includes robust error handling for common model loading issues like gated repositories or network errors. The `chat` method prepares a list of messages into a single concatenated input string, then generates a complete response using the loaded model, explicitly noting that it does not support token-by-token streaming. The `_prepare_input` method formats messages into a sequential text string, and `_generate_response` executes the model's generation process with configurable parameters. The `pull` method simulates downloading/loading a model by attempting to instantiate its tokenizer and model.

## Dependencies
*   `threading`
*   `sys`
*   `huggingface_hub.errors.RepositoryNotFoundError`
*   `huggingface_hub.errors.GatedRepoError`
*   `requests.exceptions`
*   `gc`
*   `torch` (deferred import)
*   `transformers.AutoModelForSeq2SeqLM` (deferred import)
*   `transformers.AutoTokenizer` (deferred import)
*   `transformers.BitsAndBytesConfig` (deferred import)
*   `core.llms.base_llm.BaseModel`
*   `core.llms.base_llm.ModelParams`
*   `core.events.Events`
*   `bitsandbytes` (conditionally imported)
*   `traceback` (conditionally imported)

## Constants & Environment
*   `quantization_bits` (initialization parameter, defaults to `0`)
*   `max_length=self.tokenizer.model_max_length` (used in `chat` method)
*   `max_new_tokens=1024` (default generation option)
*   `do_sample=True` (default generation option)
*   `top_k=50` (default generation option)
*   `top_p=0.95` (default generation option)
*   `temperature=0.7` (default generation option)
*   `bnb_4bit_quant_type="nf4"` (hardcoded in `BitsAndBytesConfig` for 4-bit)
*   `bnb_4bit_compute_dtype=torch.bfloat16` (hardcoded in `BitsAndBytesConfig` for 4-bit)
*   `bnb_4bit_use_double_quant=True` (hardcoded in `BitsAndBytesConfig` for 4-bit)