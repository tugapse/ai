import torch
import threading
import sys 
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
from huggingface_hub.errors import RepositoryNotFoundError, GatedRepoError
import requests.exceptions 
import gc # Import garbage collector

from core.llms.base_llm import BaseModel, ModelParams
from core.events import Events 

class HuggingFaceModel(BaseModel):
    """
    Integrates Hugging Face models as an LLM. Handles loading, quantization, and streaming responses.
    """
    def __init__(self, model_name: str, system_prompt=None, quantize=False, **kargs):
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
        """Loads the tokenizer and model from Hugging Face."""
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
                load_kwargs["torch_dtype"] = torch.bfloat16 
                load_kwargs["device_map"] = "auto"
            
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name, 
                **load_kwargs,
            )
        print(f"Successfully loaded model: {self.model_name}")

    def _quantize_model(self):
        """Attempts to load the model with 8-bit quantization using bitsandbytes."""
        print(f"Attempting to load quantized model: {self.model_name}...")
        try:
            self.model = AutoModelForCausalLM.from_pretrained(
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
            print(f"WARNING: Chat history was cleaned to ensure alternating roles. Original length: {len(messages)}, Cleaned length: {len(cleaned_messages)}. Consider adjusting upstream history management.")
        
        if cleaned_messages and cleaned_messages[-1]['role'] == 'assistant' and \
           hasattr(self.tokenizer, 'chat_template') and self.tokenizer.chat_template and \
           'add_generation_prompt' in self.tokenizer.chat_template:
            print("WARNING: Chat history ends with an 'assistant' message. The model's chat template with `add_generation_prompt=True` typically expects the last message to be from the 'user' for new generation. This might lead to unexpected model behavior or a truncated response. Ensure the conversation history passed for new generation ends with a user query.")

        return cleaned_messages


    def chat(self, messages: list, images:list[str] = None, stream: bool = True, options: object = {}):
        """
        Generates a chat response from the Hugging Face model.

        Args:
            messages (list): List of message dictionaries.
            images (list[str], optional): List of image data (not implemented).
            stream (bool, optional): If True, yields tokens; otherwise, returns full response.
            options (object, optional): Additional generation options.

        Yields:
            str: Each yielded item is a string token or the full response.
        """
        if self.model is None or self.tokenizer is None:
            yield "Model loading failed during initialization. Check logs for details."
            return

        processed_messages = self._ensure_alternating_roles(messages)
        
        # Memory Clearing for GPU
        if torch.cuda.is_available():
            print("INFO: Clearing CUDA cache before generation...")
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
        pad_token_id = self.tokenizer.pad_token_id if self.tokenizer.pad_token_id is not None else self.tokenizer.eos_token_id


        if stream:
            streamer = TextIteratorStreamer(self.tokenizer, skip_prompt=True, skip_special_tokens=True)
            
            generation_kwargs = dict(
                inputs_on_device,
                max_new_tokens=max_new_tokens,
                do_sample=do_sample,
                top_k=top_k,
                top_p=top_p,
                temperature=temperature,
                pad_token_id=pad_token_id,
                streamer=streamer,
            )
            
            thread = threading.Thread(target=self.model.generate, kwargs=generation_kwargs)
            thread.start()

            for new_token in streamer:
                yield new_token
                if hasattr(self, 'close_requested') and self.close_requested:
                    break 
            
            if isinstance(self, Events):
                self.trigger(self.STREAMING_FINISHED_EVENT)

        else:
            response_text = self._generate_response(inputs_on_device, gen_options) 
            
            if isinstance(self, Events):
                self.trigger(self.STREAMING_FINISHED_EVENT)
            
            yield response_text

    def _prepare_input(self, messages: list):
        """Formats chat messages into model input."""
        if hasattr(self.tokenizer, "apply_chat_template") and self.tokenizer.apply_chat_template is not None:
            input_string = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = self.tokenizer(input_string, return_tensors="pt")
            return inputs 
        else:
            prepared_messages = []
            if self.system_prompt and not any(m['role'] == 'system' for m in messages):
                prepared_messages.append(f"System: {self.system_prompt}") 
            
            for msg in messages:
                role = msg.get('role', 'user').capitalize() 
                content = msg.get('content', '')
                prepared_messages.append(f"{role}: {content}")
            
            if messages and messages[-1].get('role') != 'assistant':
                 prepared_messages.append("Assistant:")

            input_text = "\n".join(prepared_messages)
            
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
        pad_token_id = self.tokenizer.pad_token_id if self.tokenizer.pad_token_id is not None else self.tokenizer.eos_token_id

        outputs = self.model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=do_sample,
            top_k=top_k,
            top_p=top_p,
            temperature=temperature,
            pad_token_id=pad_token_id,
        )
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        return response

    def list(self):
        """Prints info about Hugging Face models."""
        print("Hugging Face models are available on huggingface.co/models. You can search there for available models.")
        return []

    def pull(self, model_name, stream=True):
        """Simulates 'pulling' (downloading/loading) a Hugging Face model."""
        print(f"Attempting to 'pull' (download/load) Hugging Face model: {model_name}")
        try:
            _ = AutoTokenizer.from_pretrained(model_name)
            _ = AutoModelForCausalLM.from_pretrained(model_name)
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

