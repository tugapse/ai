import torch
import threading
import sys
import queue
import gc

from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer, StoppingCriteria, StoppingCriteriaList, BitsAndBytesConfig
from huggingface_hub.errors import RepositoryNotFoundError, GatedRepoError
import requests.exceptions

from core.llms.base_llm import BaseModel, ModelParams
from core.events import Events
import functions 

# Define a custom StoppingCriteria to allow external interruption
class CustomStoppingCriteria(StoppingCriteria):
    """
    Custom StoppingCriteria to stop generation when a threading.Event is set.
    """
    def __init__(self, stop_event: threading.Event):
        self.stop_event = stop_event

    def __call__(self, input_ids: torch.LongTensor, scores: torch.FloatTensor, **kwargs) -> bool:
        """
        Checks if the stop_event has been set.
        Returns True to stop generation, False to continue.
        """
        return self.stop_event.is_set()

class HuggingFaceModel(BaseModel):
    """
    Integrates Hugging Face models as an LLM. Handles loading, quantization, and streaming responses.
    """
    def __init__(self, model_name: str, system_prompt=None, quantization_bits: int = 0, **kargs):
        super().__init__(model_name, system_prompt, **kargs)
        self.tokenizer = None
        self.model = None
        self.quantization_bits = quantization_bits 
        self.error_queue = queue.Queue() # Queue to communicate errors from background thread

        try:
            self._load_llm_params()
        except GatedRepoError as e:
            functions.log(f"ERROR: Failed to load gated model '{self.model_name}'. Access denied or not authenticated. Details: {e}")
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
            traceback.print_exc() # Corrected: functions.log_exc() to print_exc()
            self.model = None
            self.tokenizer = None
            sys.exit(1)

    def _load_llm_params(self):
        """Loads the tokenizer and model from Hugging Face."""
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
                import bitsandbytes as bnb # noqa: F401 - This import is for check, not direct use of bnb functions here
                if self.quantization_bits == 4:
                    quantization_config = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_quant_type="nf4", # Recommended 4-bit quantization type
                        bnb_4bit_compute_dtype=torch.bfloat16, # Compute in bfloat16 for better performance
                        bnb_4bit_use_double_quant=True, # Optional: enables nested quantization
                    )
                    functions.log("INFO: Configured for 4-bit quantization using BitsAndBytesConfig.")
                elif self.quantization_bits == 8:
                    quantization_config = BitsAndBytesConfig(load_in_8bit=True)
                    functions.log("INFO: Configured for 8-bit quantization using BitsAndBytesConfig.")
                
            except ImportError:
                functions.log("WARNING: bitsandbytes not found. Quantization requires `pip install bitsandbytes accelerate` and a compatible CUDA setup.")
                functions.log("Falling back to non-quantized loading (might require more VRAM).")
                self.quantization_bits = 0 # Reset quantization to none
            except Exception as e:
                functions.log(f"ERROR: Could not create BitsAndBytesConfig for {self.quantization_bits}-bit quantization: {e}")
                functions.log("Falling back to non-quantized loading.")
                self.quantization_bits = 0 # Reset quantization to none
        
        if quantization_config:
            load_kwargs["quantization_config"] = quantization_config
            if torch.cuda.is_available():
                load_kwargs["device_map"] = "auto"
            functions.log(f"Attempting to load model: {self.model_name} with {self.quantization_bits}-bit quantization config.")
        else:
            functions.log("INFO: Loading model without quantization (either not requested or bitsandbytes not available/failed).")
            if torch.cuda.is_available():
                load_kwargs["torch_dtype"] = torch.bfloat16 # Use bfloat16 for better precision on newer GPUs
                load_kwargs["device_map"] = "auto"

        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            **load_kwargs,
        )
        functions.log(f"Successfully loaded model: {self.model_name}")

    def _ensure_alternating_roles(self, messages: list) -> list:
        """Ensures conversation roles alternate (user/assistant) and merges consecutive messages."""
        if not messages:
            return []

        cleaned_messages = []
        system_messages = [msg for msg in messages if msg['role'] == 'system']
        other_messages = [msg for msg in messages if msg['role'] != 'system']

        if system_messages:
            cleaned_messages.extend(system_messages)

        if not other_messages:
            return cleaned_messages

        current_message = {"role": other_messages[0]['role'], "content": other_messages[0]['content']}

        for i in range(1, len(other_messages)):
            msg = other_messages[i]
            if msg['role'] == current_message['role']:
                current_message['content'] += "\n" + msg['content']
            else:
                cleaned_messages.append(current_message)
                current_message = {"role": msg['role'], "content": msg['content']}

        cleaned_messages.append(current_message)

        if len(cleaned_messages) < len(messages):
            functions.log(f"WARNING: Chat history was cleaned to ensure alternating roles. Original length: {len(messages)}, Cleaned length: {len(cleaned_messages)}. Consider adjusting upstream history management.")

        return cleaned_messages

    def _generate_in_thread(self, model, generation_kwargs, error_queue, streamer, stop_event: threading.Event):
        """
        Target function for the generation thread.
        Handles model generation and puts any caught exceptions into the error_queue.
        """
        try:
            generation_kwargs['stopping_criteria'] = StoppingCriteriaList([CustomStoppingCriteria(stop_event)])
            model.generate(**generation_kwargs)
        except RuntimeError as e:
            error_message = (
                f"\nERROR: Model generation failed due to a CUDA/Runtime error. "
                f"This often indicates numerical instability or memory issues during generation."
                f"\nDetails: {e}"
                f"\nSuggestion: Try reducing 'temperature' (e.g., to 0.5 or 0.3), or disable sampling (`do_sample=False`) "
                f"in your model configuration. If the issue persists, consider a smaller model or more VRAM, or ensure bitsandbytes is correctly installed for {self.quantization_bits}-bit quantization."
            )
            error_queue.put(error_message)
            streamer.end()
        except Exception as e:
            import traceback
            error_message = f"\nCRITICAL ERROR: An unexpected error occurred during model generation: {e}"
            error_message += f"\nTraceback:\n{traceback.format_exc()}"
            error_queue.put(error_message)
            streamer.end()

    def join_generation_thread(self, timeout: float = None):
        """
        Waits for the background generation thread to complete.
        Overrides BaseModel's method.
        """
        if self._generation_thread and self._generation_thread.is_alive():
            functions.log("INFO: Waiting for HuggingFace LLM generation thread to finish...")
            self._generation_thread.join(timeout=timeout)
            if self._generation_thread.is_alive():
                functions.log("WARNING: HuggingFace LLM generation thread did not terminate within timeout.")
        self.stop_generation_event.clear()


    def chat(self, messages: list, images:list[str] = None, stream: bool = True, options: object = {}):
        """
        Generates a chat response from the Hugging Face model.
        """
        if self.model is None or self.tokenizer is None:
            yield "Model loading failed during initialization. Check logs for details."
            return

        self.stop_generation_event.clear()

        processed_messages = self._ensure_alternating_roles(messages)

        if torch.cuda.is_available():
            functions.log("INFO: Clearing CUDA cache before generation...")
            torch.cuda.empty_cache()
            gc.collect()

        input_data = self._prepare_input(processed_messages)

        if torch.cuda.is_available():
            inputs_on_device = {k: v.to('cuda') for k, v in input_data.items()}
        else:
            inputs_on_device = input_data

        gen_options = self.options.to_dict() if hasattr(self, 'options') and self.options else {}
        gen_options.update(options)

        max_new_tokens = gen_options.get('max_new_tokens', 1024)
        do_sample = gen_options.get('do_sample', True)
        top_k = gen_options.get('top_k', 50)
        top_p = gen_options.get('top_p', 0.95)
        temperature = gen_options.get('temperature', 0.7)
        
        eos_token_id = self.tokenizer.eos_token_id 
        if eos_token_id is None and hasattr(self.tokenizer, 'pad_token_id'):
            eos_token_id = self.tokenizer.pad_token_id 
        elif eos_token_id is None: 
            functions.log("WARNING: No EOS or PAD token ID found for tokenizer. Model generation might not terminate cleanly.")
            eos_token_id = -1 

        # Initialize streamer to None *before* it's used in generation_kwargs
        streamer = None 

        generation_kwargs = dict(
            inputs_on_device,
            max_new_tokens=max_new_tokens,
            do_sample=do_sample,
            top_k=top_k,
            top_p=top_p,
            temperature=temperature,
            pad_token_id=eos_token_id, 
            eos_token_id=eos_token_id, 
            streamer=streamer if stream else None, # Now streamer is guaranteed to be defined
        )

        if stream:
            # IMPORTANT: Set skip_special_tokens=False. We want all non-EOS tokens (including emojis)
            # to be yielded by the streamer. Program.py will manually filter the specific EOS token.
            streamer = TextIteratorStreamer(self.tokenizer, skip_prompt=True, skip_special_tokens=True)
            generation_kwargs["streamer"] = streamer # Update streamer in kwargs after creation

            self._generation_thread = threading.Thread(
                target=self._generate_in_thread,
                kwargs={
                    "model": self.model,
                    "generation_kwargs": generation_kwargs,
                    "error_queue": self.error_queue,
                    "streamer": streamer,
                    "stop_event": self.stop_generation_event
                }
            )
            self._generation_thread.start()

            for new_token in streamer:
                yield new_token 
                if not self.error_queue.empty():
                    error_message = self.error_queue.get()
                    functions.log(error_message)
                    sys.exit(1)

            if not self.error_queue.empty():
                error_message = self.error_queue.get()
                functions.log(error_message)
                sys.exit(1)

            if isinstance(self, Events):
                self.trigger(self.STREAMING_FINISHED_EVENT)

        else:
            try:
                response_text = self._generate_response(inputs_on_device, gen_options)

                if isinstance(self, Events):
                    self.trigger(self.STREAMING_FINISHED_EVENT)

                yield response_text
            except RuntimeError as e:
                functions.log(f"\nERROR: Model generation failed due to a CUDA/Runtime error. This often indicates numerical instability or memory issues during generation.")
                functions.log(f"Details: {e}")
                functions.log(f"Suggestion: Try reducing 'temperature' (e.g., to 0.5 or 0.3), or disable sampling (`do_sample=False`) in your model configuration. If the issue persists, consider a smaller model or more VRAM, or ensure bitsandbytes is correctly installed for {self.quantization_bits}-bit quantization.")
                sys.exit(1)
            except Exception as e:
                functions.log(f"\nCRITICAL ERROR: An unexpected error occurred during model generation: {e}")
                import traceback
                traceback.print_exc() # Corrected: functions.log_exc() to print_exc()
                sys.exit(1)

    def _prepare_input(self, messages: list):
        """
        Formats chat messages into model input, ensuring the last turn is for the assistant to generate.
        This handles models with and without `apply_chat_template`.
        """
        if hasattr(self.tokenizer, "apply_chat_template") and self.tokenizer.apply_chat_template is not None:
            input_string = self.tokenizer.apply_chat_template(
                messages, 
                tokenize=False, 
                add_generation_prompt=True
            )
            inputs = self.tokenizer(input_string, return_tensors="pt")
            return inputs
        else:
            prepared_messages = []
            if self.system_prompt and not any(m['role'] == 'system' for m in messages):
                prepared_messages.append(BaseModel.create_message("system", self.system_prompt))

            for msg in messages:
                role = msg.get('role', 'user')
                content = msg.get('content', '')
                prepared_messages.append(BaseModel.create_message(role, content))
            
            input_text = ""
            for msg in prepared_messages:
                if msg['role'] == 'system':
                    input_text += f"System: {msg['content']}\n"
                elif msg['role'] == 'user':
                    input_text += f"User: {msg['content']}\n"
                elif msg['role'] == 'assistant':
                    input_text += f"Assistant: {msg['content']}\n"
            
            if messages and messages[-1]['role'] == 'user':
                input_text += "Assistant:"

            inputs = self.tokenizer(input_text, return_tensors="pt")
            return inputs

    def _generate_response(self, input_data, options: dict = {}):
        """Generates a complete response without streaming."""
        if self.model is None or self.tokenizer is None:
            return "Model not loaded."

        inputs = input_data

        max_new_tokens = options.get('max_new_tokens', 1024)
        do_sample = options.get('do_sample', True)
        top_k = options.get('top_k', 50)
        top_p = options.get('top_p', 0.95)
        temperature = options.get('temperature', 0.7)
        
        eos_token_id = self.tokenizer.eos_token_id 
        if eos_token_id is None and hasattr(self.tokenizer, 'pad_token_id'):
            eos_token_id = self.tokenizer.pad_token_id 
        elif eos_token_id is None: 
            functions.log("WARNING: No EOS or PAD token ID found for tokenizer. Model generation might not terminate cleanly.")
            eos_token_id = -1 


        outputs = self.model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=do_sample,
            top_k=top_k,
            top_p=top_p,
            temperature=temperature,
            pad_token_id=eos_token_id, 
            eos_token_id=eos_token_id, 
        )
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        return response

    def list(self):
        """functions.logs info about Hugging Face models."""
        functions.log("Hugging Face models are available on huggingface.co/models. You can search there for available models.")
        return []

    def pull(self, model_name, stream=True):
        """Simulates 'pulling' (downloading/loading) a Hugging Face model."""
        functions.log(f"Attempting to 'pull' (download/load) Hugging Face model: {model_name}")
        try:
            _ = AutoTokenizer.from_pretrained(model_name)
            _ = AutoModelForCausalLM.from_pretrained(model_name)
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
