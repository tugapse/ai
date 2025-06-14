import torch
import threading
import sys
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, TextIteratorStreamer
from huggingface_hub.errors import RepositoryNotFoundError, GatedRepoError
import requests.exceptions
import gc # Import garbage collector

from core.llms.base_llm import BaseModel, ModelParams
from core.events import Events

class T5Model(BaseModel):
    """
    Integrates T5-type (encoder-decoder / Seq2Seq) Hugging Face models.
    This model is typically used for tasks like summarization or translation,
    and handles chat by processing the full conversation context as a single input.
    """
    def __init__(self, model_name: str, system_prompt=None, quantize=False, **kargs):
        """
        Initializes the T5Model instance.

        Args:
            model_name (str): The identifier of the Hugging Face T5 model.
            system_prompt (str, optional): A system prompt for the model. Defaults to None.
            quantize (bool, optional): Whether to load the model with 8-bit quantization. Defaults to False.
            **kargs: Additional keyword arguments passed to the BaseModel constructor.
        """
        super().__init__(model=model_name, system_prompt=system_prompt, **kargs)
        self.tokenizer = None
        self.model = None
        self.quantize = quantize

        try:
            self._load_llm_params()
        except GatedRepoError as e:
            print(f"\n--- MODEL LOADING FAILED: Gated Model Access Required ---")
            print(f"To use '{self.model_name}', you need to:")
            print(f"1. Request access on Hugging Face: {e.url.replace('/resolve/main/', '/')}")
            print(f"2. Log in to Hugging Face from your terminal: `huggingface-cli login`")
            print(f"   (Get your token from: https://huggingface.co/settings/tokens)")
            print(f"----------------------------------------------------\n")
            self.model = None
            self.tokenizer = None
            sys.exit(1)
        except RepositoryNotFoundError:
            print(f"Error: Model '{self.model_name}' not found on Hugging Face Hub. Check spelling.")
            self.model = None
            self.tokenizer = None
            sys.exit(1)
        except requests.exceptions.HTTPError as e:
            print(f"Error: Could not download model files for '{self.model_name}'. Check network, disk space, or proxy settings.")
            print(f"Details: {e}")
            self.model = None
            self.tokenizer = None
            sys.exit(1)
        except Exception as e:
            print(f"CRITICAL ERROR: Model initialization failed for {self.model_name}: {e}")
            import traceback
            traceback.print_exc()
            self.model = None
            self.tokenizer = None
            sys.exit(1)

    def _load_llm_params(self):
        """Loads the tokenizer and Seq2Seq model from Hugging Face."""
        print(f"Attempting to load model: {self.model_name}...")

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            trust_remote_code=True,
        )
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        if self.quantize:
            self._quantize_model()
        else:
            load_kwargs = {"trust_remote_code": True}
            if torch.cuda.is_available():
                # T5 models often use float32 or bfloat16. Check model card for optimal dtype.
                # Using bfloat16 for memory efficiency.
                load_kwargs["torch_dtype"] = torch.bfloat16
                load_kwargs["device_map"] = "auto"

            # Use AutoModelForSeq2SeqLM for T5-type models
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                self.model_name,
                **load_kwargs,
            )
        print(f"Successfully loaded model: {self.model_name}")

    def _quantize_model(self):
        """Attempts to load the Seq2Seq model with 8-bit quantization using bitsandbytes."""
        print(f"Attempting to load quantized model: {self.model_name}...")
        try:
            self.model = AutoModelForSeq2SeqLM.from_pretrained(
                self.model_name,
                load_in_8bit=True,
                device_map="auto",
                trust_remote_code=True,
            )
            print(f"Successfully loaded quantized model: {self.model_name}")
        except ImportError:
            print("Error: bitsandbytes not installed or compatible. Attempting to load non-quantized model.")
            self.quantize = False
            self._load_llm_params()
        except Exception as e:
            print(f"Error during quantization model loading: {e}")
            print("Attempting to load non-quantized model as a fallback.")
            self.quantize = False
            self._load_llm_params()

    def chat(self, messages: list, images:list[str] = None, stream: bool = True, options: object = {}):
        """
        Generates a response from the T5 model. For T5, 'chat' means processing
        the entire context to generate a single output, typically summarization or response.
        Streaming will not yield token by token but return the full response at once.

        Args:
            messages (list): List of message dictionaries representing the conversation history.
            images (list[str], optional): List of image data (not implemented).
            stream (bool, optional): If True, will still return full response. Token-by-token streaming not supported.
            options (object, optional): Additional generation options.

        Yields:
            str: The generated response.
        """
        if self.model is None or self.tokenizer is None:
            yield "Model loading failed during initialization. Check logs for details."
            return

        # T5 models typically don't have a chat template like causal LMs.
        # We'll concatenate messages for context.
        context_string = self._prepare_input(messages)

        # Memory Clearing for GPU
        if torch.cuda.is_available():
            print("INFO: Clearing CUDA cache before generation...")
            torch.cuda.empty_cache()
            gc.collect()

        # T5-type models use encode/decode for generation
        inputs = self.tokenizer(
            context_string, 
            return_tensors="pt", 
            max_length=self.tokenizer.model_max_length, 
            truncation=True
        )

        if torch.cuda.is_available():
            inputs_on_device = {k: v.to('cuda') for k, v in inputs.items()}
        else:
            inputs_on_device = inputs

        gen_options = self.options.to_dict() if hasattr(self, 'options') and self.options else {}
        gen_options.update(options)

        max_new_tokens = gen_options.get('max_new_tokens', 1024)
        # Note: T5 generation parameters might differ slightly from causal LMs.
        # Common ones are num_beams for beam search, min_length etc.
        # For simplicity, we'll keep common generation parameters for now.
        do_sample = gen_options.get('do_sample', True)
        top_k = gen_options.get('top_k', 50)
        top_p = gen_options.get('top_p', 0.95)
        temperature = gen_options.get('temperature', 0.7)
        pad_token_id = self.tokenizer.pad_token_id if self.tokenizer.pad_token_id is not None else self.tokenizer.eos_token_id


        # T5 generation uses `generate` on the model directly, not TextIteratorStreamer
        # for token-by-token streaming in the same way.
        # So, we'll perform non-streaming generation and yield the full result.
        
        # We use a thread only if we wanted true streaming, but for Seq2Seq, it's more complex.
        # For now, we simplify to full response.
        
        print("INFO: T5Model does not support token-by-token streaming directly for chat. Returning full response.")
        
        # Use the _generate_response helper
        response_text = self._generate_response(inputs_on_device, gen_options)
        
        # Trigger stream finished event as the full response is available.
        if isinstance(self, Events):
            self.trigger(self.STREAMING_FINISHED_EVENT)
        
        yield response_text


    def _prepare_input(self, messages: list):
        """
        Prepares the input string for T5 models by concatenating conversation messages.
        T5 models often expect a single input string for tasks like summarization.
        """
        prepared_input_parts = []
        if self.system_prompt:
            prepared_input_parts.append(f"System: {self.system_prompt}")

        for msg in messages:
            role = msg.get('role', 'user').capitalize()
            content = msg.get('content', '')
            prepared_input_parts.append(f"{role}: {content}")

        # Join all parts to form the single input string for the T5 encoder
        # For a summarization model, you might just concatenate the user/assistant turns
        # without explicit roles if the model expects pure text.
        # Example for summarization model: "summarize: " + "\n".join(all_messages)
        # For general response, this format is reasonable.
        return "\n".join(prepared_input_parts)

    def _generate_response(self, inputs_on_device, options: dict = {}):
        """Generates a complete response from the T5 model."""
        if self.model is None or self.tokenizer is None:
            return "Model not loaded."

        max_new_tokens = options.get('max_new_tokens', 1024)
        do_sample = options.get('do_sample', True)
        top_k = options.get('top_k', 50)
        top_p = options.get('top_p', 0.95)
        temperature = options.get('temperature', 0.7)
        # T5 typically doesn't use pad_token_id in `generate` in the same way for output.
        # It's more about `decoder_start_token_id` for its own generation.
        # We'll pass common params, and Hugging Face's generate will use what's applicable.

        # T5 generation typically requires `decoder_input_ids` or `decoder_start_token_id`
        # We will let the generate method figure this out if not explicitly provided.
        # For T5, this is usually `tokenizer.pad_token_id` or `tokenizer.eos_token_id`
        # depending on the specific model.
        
        generation_output = self.model.generate(
            input_ids=inputs_on_device["input_ids"],
            attention_mask=inputs_on_device["attention_mask"],
            max_new_tokens=max_new_tokens,
            do_sample=do_sample,
            top_k=top_k,
            top_p=top_p,
            temperature=temperature,
            # decoder_start_token_id=self.tokenizer.pad_token_id # Often useful for T5
        )
        response_text = self.tokenizer.decode(generation_output[0], skip_special_tokens=True)

        return response_text

    def list(self):
        """Prints info about Hugging Face models."""
        print("Hugging Face models are available on huggingface.co/models. You can search there for available models.")
        return []

    def pull(self, model_name, stream=True):
        """Simulates 'pulling' (downloading/loading) a Hugging Face model."""
        print(f"Attempting to 'pull' (download/load) Hugging Face model: {model_name}")
        try:
            _ = AutoTokenizer.from_pretrained(model_name)
            # Use AutoModelForSeq2SeqLM for pulling T5 models
            _ = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            message = f"Model {model_name} 'pulled' (downloaded/loaded) successfully."
            print(message)
            if stream:
                yield message
            else:
                return message
        except Exception as e:
            message = f"Error 'pulling' model {model_name}: {e}"
            print(message)
            if stream:
                yield message
            else:
                return message
