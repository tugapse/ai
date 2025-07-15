import torch
import threading
import sys
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, TextIteratorStreamer, BitsAndBytesConfig
from huggingface_hub.errors import RepositoryNotFoundError, GatedRepoError
import requests.exceptions
import gc

from core.llms.base_llm import BaseModel, ModelParams
from core.events import Events

class T5Model(BaseModel):
    """
    Integrates T5-type (encoder-decoder / Seq2Seq) Hugging Face models.
    This model is typically used for tasks like summarization or translation,
    and handles chat by processing the full conversation context as a single input.
    """
    def __init__(self, model_name: str, system_prompt=None, quantization_bits: int = 0, **kargs):
        """
        Initializes the T5Model instance.

        Args:
            model_name (str): The identifier of the Hugging Face T5 model.
            system_prompt (str, optional): A system prompt for the model. Defaults to None.
            quantization_bits (int, optional): Whether to load the model with X-bit quantization (0 for none). Defaults to 0.
            **kargs: Additional keyword arguments passed to the BaseModel constructor.
        """
        super().__init__(model_name, system_prompt, **kargs)
        self.tokenizer = None
        self.model = None
        self.quantization_bits = quantization_bits 

        try:
            self._load_llm_params()
        except GatedRepoError as e:
            functions.log(f"\n--- MODEL LOADING FAILED: Gated Model Access Required ---")
            functions.log(f"To use '{self.model_name}', you need to:")
            functions.log(f"1. Request access on Hugging Face: {e.url.replace('/resolve/main/', '/')}")
            functions.log(f"2. Log in to Hugging Face from your terminal: `huggingface-cli login`")
            functions.log(f"   (Get your token from: https://huggingface.co/settings/tokens)")
            functions.log(f"----------------------------------------------------\n")
            self.model = None
            self.tokenizer = None
            sys.exit(1)
        except RepositoryNotFoundError:
            functions.log(f"Error: Model '{self.model_name}' not found on Hugging Face Hub. Check spelling.")
            self.model = None
            self.tokenizer = None
            sys.exit(1)
        except requests.exceptions.HTTPError as e:
            functions.log(f"Error: Could not download model files for '{self.model_name}'. Check network, disk space, or proxy settings.")
            functions.log(f"Details: {e}")
            self.model = None
            self.tokenizer = None
            sys.exit(1)
        except Exception as e:
            functions.log(f"CRITICAL ERROR: Model initialization failed for {self.model_name}: {e}")
            import traceback
            traceback.functions.log_exc()
            self.model = None
            self.tokenizer = None
            sys.exit(1)

    def _load_llm_params(self):
        """Loads the tokenizer and Seq2Seq model from Hugging Face."""
        functions.log(f"Attempting to load model: {self.model_name}...")

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name,
            trust_remote_code=True,
        )
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        load_kwargs = {"trust_remote_code": True}
        
        quantization_config = None
        if self.quantization_bits in [4, 8]:
            try:
                import bitsandbytes as bnb # noqa: F401
                if self.quantization_bits == 4:
                    quantization_config = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_quant_type="nf4",
                        bnb_4bit_compute_dtype=torch.bfloat16,
                        bnb_4bit_use_double_quant=True,
                    )
                    functions.log("INFO: Configured for 4-bit quantization using BitsAndBytesConfig.")
                elif self.quantization_bits == 8:
                    quantization_config = BitsAndBytesConfig(load_in_8bit=True)
                    functions.log("INFO: Configured for 8-bit quantization using BitsAndBytesConfig.")
            except ImportError:
                functions.log("WARNING: bitsandbytes not found. Quantization requires `pip install bitsandbytes accelerate` and a compatible CUDA setup.")
                functions.log("Falling back to non-quantized loading.")
                self.quantization_bits = 0
            except Exception as e:
                functions.log(f"ERROR: Could not create BitsAndBytesConfig for {self.quantization_bits}-bit quantization: {e}")
                functions.log("Falling back to non-quantized loading.")
                self.quantization_bits = 0

        if quantization_config:
            load_kwargs["quantization_config"] = quantization_config
            if self.is_gpu_available():
                load_kwargs["device_map"] = "auto"
            functions.log(f"Attempting to load model: {self.model_name} with {self.quantization_bits}-bit quantization config.")
        else:
            functions.log("INFO: Loading model without quantization (either not requested or bitsandbytes not available/failed).")
            if self.is_gpu_available():
                load_kwargs["torch_dtype"] = torch.bfloat16
                load_kwargs["device_map"] = "auto"

        self.model = AutoModelForSeq2SeqLM.from_pretrained(
            self.model_name,
            **load_kwargs,
        )
        functions.log(f"Successfully loaded model: {self.model_name}")

    def chat(self, messages: list, images:list[str] = None, stream: bool = True, options: object = {}):
        """
        Generates a response from the T5 model. For T5, 'chat' means processing
        the entire context to generate a single output, typically summarization or response.
        Streaming will not yield token by token but return the full response at once.
        """
        if self.model is None or self.tokenizer is None:
            yield "Model loading failed during initialization. Check logs for details."
            return

        context_string = self._prepare_input(messages)

        if self.is_gpu_available():
            functions.log("INFO: Clearing CUDA cache before generation...")
            torch.cuda.empty_cache()
            gc.collect()

        inputs = self.tokenizer(
            context_string, 
            return_tensors="pt", 
            max_length=self.tokenizer.model_max_length, 
            truncation=True
        )

        if self.is_gpu_available():
            inputs_on_device = {k: v.to('cuda') for k, v in inputs.items()}
        else:
            inputs_on_device = inputs

        gen_options = self.options.to_dict() if hasattr(self, 'options') and self.options else {}
        gen_options.update(options)

        max_new_tokens = gen_options.get('max_new_tokens', 1024)
        do_sample = gen_options.get('do_sample', True)
        top_k = gen_options.get('top_k', 50)
        top_p = gen_options.get('top_p', 0.95)
        temperature = gen_options.get('temperature', 0.7)
        
        functions.log("INFO: T5Model does not support token-by-token streaming directly for chat. Returning full response.")
        
        try:
            response_text = self._generate_response(inputs_on_device, gen_options)
            
            if isinstance(self, Events):
                self.trigger(self.STREAMING_FINISHED_EVENT)
            
            yield response_text
        except KeyboardInterrupt:
            functions.log("\nINFO: Ctrl+C detected. Stopping T5Model generation...")
            if isinstance(self, Events):
                self.trigger(self.STREAMING_FINISHED_EVENT)
        except Exception as e:
            functions.log(f"\nCRITICAL ERROR: An unexpected error occurred during T5Model generation: {e}")
            import traceback
            traceback.functions.log_exc()
            sys.exit(1)


    def _prepare_input(self, messages: list):
        """
        Prepares the input string for T5 models by concatenating conversation messages.
        T5 models often expect a single input string for tasks like summarization.
        """
        prepared_input_parts = []
        if self.system_prompt:
            prepared_input_parts.append(BaseModel.create_message("system", self.system_prompt))

        for msg in messages:
            role = msg.get('role', 'user').capitalize()
            content = msg.get('content', '')
            prepared_input_parts.append(BaseModel.create_message(role, content))

        input_text = ""
        for msg in prepared_input_parts:
            if msg['role'] == 'system':
                input_text += f"System: {msg['content']}\n"
            elif msg['role'] == 'user':
                input_text += f"User: {msg['content']}\n"
            elif msg['role'] == 'assistant':
                input_text += f"Assistant: {msg['content']}\n"
        
        inputs = self.tokenizer(input_text, return_tensors="pt")
        return inputs

    def _generate_response(self, inputs_on_device, options: dict = {}):
        """Generates a complete response from the T5 model."""
        if self.model is None or self.tokenizer is None:
            return "Model not loaded."

        max_new_tokens = options.get('max_new_tokens', 1024)
        do_sample = options.get('do_sample', True)
        top_k = options.get('top_k', 50)
        top_p = options.get('top_p', 0.95)
        temperature = options.get('temperature', 0.7)
        
        generation_output = self.model.generate(
            input_ids=inputs_on_device["input_ids"],
            attention_mask=inputs_on_device["attention_mask"],
            max_new_tokens=max_new_tokens,
            do_sample=do_sample,
            top_k=top_k,
            top_p=top_p,
            temperature=temperature,
        )
        response_text = self.tokenizer.decode(generation_output[0], skip_special_tokens=True)

        return response_text

    def list(self):
        """functions.logs info about Hugging Face models."""
        functions.log("Hugging Face models are available on huggingface.co/models. You can search there for available models.")
        return []

    def pull(self, model_name, stream=True):
        """Simulates 'pulling' (downloading/loading) a Hugging Face model."""
        functions.log(f"Attempting to 'pull' (download/load) Hugging Face model: {model_name}")
        try:
            _ = AutoTokenizer.from_pretrained(model_name)
            _ = AutoModelForSeq2SeqLM.from_pretrained(model_name)
            message = f"Model {model_name} 'pulled' (downloaded/loaded) successfully."
            functions.log(message)
            if stream:
                yield message
            else:
                return message
        except Exception as e:
            message = f"Error 'pulling' model {model_name}: {e}"
            functions.log(message)
            if stream:
                yield message
            else:
                return message
