import torch
import threading
import sys 
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
from huggingface_hub.errors import RepositoryNotFoundError, GatedRepoError
import requests.exceptions 

# Assuming BaseModel and ModelParams are correctly defined in core.llms.base_llm
from core.llms.base_llm import BaseModel, ModelParams

# Assuming Events is correctly defined in core.events
from core.events import Events 

class HuggingFaceModel(BaseModel):
    """
    A class to integrate Hugging Face models as an LLM within the application.
    It handles model loading, quantization, and streaming chat responses.
    """
    def __init__(self, model_name: str, system_prompt=None, quantize=False, **kargs):
        """
        Initializes the HuggingFaceModel instance.

        Args:
            model_name (str): The identifier of the Hugging Face model (e.g., "google/gemma-3-4b-it").
            system_prompt (str, optional): An initial system prompt for the model. Defaults to None.
            quantize (bool, optional): Whether to load the model with 8-bit quantization. Defaults to False.
            **kargs: Additional keyword arguments passed to the BaseModel constructor.
        """
        super().__init__(model=model_name, system_prompt=system_prompt, **kargs)
        self.tokenizer = None
        self.model = None
        self.quantize = quantize 
        
        # Attempt to load the model during initialization, with robust error handling.
        try:
            self._load_llm_params() 
        except GatedRepoError as e: 
            # Specific error handling for gated models requiring Hugging Face login/access.
            print(f"\n--- MODEL LOADING FAILED: Gated Model Access Required ---")
            print(f"To use '{self.model_name}', you need to:")
            print(f"1. Request access on Hugging Face: {e.url.replace('/resolve/main/', '/')}")
            print(f"2. Log in to Hugging Face from your terminal: `huggingface-cli login`")
            print(f"   (Get your token from: https://huggingface.co/settings/tokens)")
            print(f"----------------------------------------------------\n")
            self.model = None
            self.tokenizer = None
            sys.exit(1) # Exit application on gated repo error
        except RepositoryNotFoundError:
            # Error handling for models not found on the Hugging Face Hub.
            print(f"Error: Model '{self.model_name}' not found on Hugging Face Hub. Check spelling.")
            self.model = None
            self.tokenizer = None
            sys.exit(1) # Exit application on model not found
        except requests.exceptions.HTTPError as e: 
            # General HTTP error handling for network/download issues.
            print(f"Error: Could not download model files for '{self.model_name}'. Check network, disk space, or proxy settings.")
            print(f"Details: {e}")
            self.model = None
            self.tokenizer = None
            sys.exit(1) # Exit application on download error
        except Exception as e: # Catch any other unexpected errors during initialization
            print(f"CRITICAL ERROR: Model initialization failed for {self.model_name}: {e}")
            import traceback
            traceback.print_exc() # Print full traceback for detailed debugging
            self.model = None
            self.tokenizer = None
            sys.exit(1) # Exit application on any critical loading error

    def _load_llm_params(self):
        """
        Loads the tokenizer and model from Hugging Face.
        This method is called during initialization and handles the core loading logic.
        """
        print(f"Attempting to load model: {self.model_name}...")
        
        # Load the tokenizer. trust_remote_code is necessary for some custom model architectures.
        self.tokenizer = AutoTokenizer.from_pretrained(
            self.model_name, 
            trust_remote_code=True,
        )
        # Ensure a pad_token is set for consistency; many models default to eos_token if none is specified.
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        if self.quantize: 
            self._quantize_model() # Attempt to load quantized model
        else:
            # Load the full precision model, potentially using bfloat16 and auto device mapping
            load_kwargs = {"trust_remote_code": True}
            if torch.cuda.is_available():
                # Use bfloat16 for reduced memory footprint if GPU is available
                # Gemma models were often trained in bfloat16.
                load_kwargs["torch_dtype"] = torch.bfloat16 
                # device_map="auto" distributes layers across GPU and CPU if needed.
                load_kwargs["device_map"] = "auto"
            
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name, 
                **load_kwargs,
            )
        print(f"Successfully loaded model: {self.model_name}")

        # Removed the explicit self.model.to('cuda')
        # device_map="auto" handles device placement, so manual .to('cuda') is not needed
        # and can conflict with accelerate's memory management.

    def _quantize_model(self):
        """
        Attempts to load the model with 8-bit quantization using bitsandbytes.
        Includes fallback to non-quantized loading if quantization fails.
        """
        print(f"Attempting to load quantized model: {self.model_name}...")
        try:
            # load_in_8bit=True activates 8-bit quantization.
            # device_map="auto" intelligently distributes the model across available GPUs/CPU.
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name, 
                load_in_8bit=True, # For 4-bit, use load_in_4bit=True with a proper QuantizationConfig
                device_map="auto", # Crucial for bitsandbytes for efficient GPU utilization
                trust_remote_code=True,
            )
            print(f"Successfully loaded quantized model: {self.model_name}")
        except ImportError:
            # Fallback if bitsandbytes is not installed or compatible.
            print("Error: bitsandbytes not installed or compatible. Attempting to load non-quantized model.")
            self.quantize = False # Disable quantization for this instance
            self._load_llm_params() # Recursively try loading non-quantized
        except Exception as e:
            # Fallback for other quantization-specific errors.
            print(f"Error during quantization model loading: {e}")
            print("Attempting to load non-quantized model as a fallback.")
            self.quantize = False
            self._load_llm_params()

    def _ensure_alternating_roles(self, messages: list) -> list:
        """
        Ensures that conversation roles alternate (user/assistant) and merges
        consecutive messages from the same role.
        System messages are assumed to be at the very beginning and are handled separately.
        """
        if not messages:
            return []

        cleaned_messages = []
        
        # Separate system messages from other conversation turns
        system_messages = [msg for msg in messages if msg['role'] == 'system']
        other_messages = [msg for msg in messages if msg['role'] != 'system']

        if system_messages:
            cleaned_messages.extend(system_messages)
        
        if not other_messages:
            # Only system messages or no messages at all, no alternation needed here.
            return cleaned_messages 

        # Process non-system messages to ensure alternation
        current_message = {"role": other_messages[0]['role'], "content": other_messages[0]['content']}
        
        for i in range(1, len(other_messages)):
            msg = other_messages[i]
            if msg['role'] == current_message['role']:
                # Merge content if roles are consecutive
                current_message['content'] += "\n" + msg['content']
            else:
                # Add the accumulated message and start a new one
                cleaned_messages.append(current_message)
                current_message = {"role": msg['role'], "content": msg['content']}
        
        # Add the last accumulated message
        cleaned_messages.append(current_message) 

        # Optional: Warn if cleaning was performed
        if len(cleaned_messages) < len(messages):
            print(f"WARNING: Chat history was cleaned to ensure alternating roles. Original length: {len(messages)}, Cleaned length: {len(cleaned_messages)}. Consider adjusting upstream history management.")
        
        # Additional check for model generation prompt: if the chat template expects
        # generation after a user turn, but the history ends with an assistant message,
        # it might still cause issues. This is a warning, not a fix here.
        if cleaned_messages and cleaned_messages[-1]['role'] == 'assistant' and \
           hasattr(self.tokenizer, 'chat_template') and self.tokenizer.chat_template and \
           'add_generation_prompt' in self.tokenizer.chat_template:
            print("WARNING: Chat history ends with an 'assistant' message. The model's chat template with `add_generation_prompt=True` typically expects the last message to be from the 'user' for new generation. This might lead to unexpected model behavior or a truncated response. Ensure the conversation history passed for new generation ends with a user query.")

        return cleaned_messages


    def chat(self, messages: list, images:list[str] = None, stream: bool = True, options: object = {}):
        """
        Generates a chat response from the Hugging Face model.

        Args:
            messages (list): A list of message dictionaries (e.g., [{"role": "user", "content": "Hello"}]).
            images (list[str], optional): List of image data (not implemented for HF models in this code).
            stream (bool, optional): If True, yields tokens one by one; otherwise, returns the full response. Defaults to True.
            options (object, optional): Additional generation options for the model (e.g., max_new_tokens, temperature).

        Yields:
            str: Each yielded item is a string token if streaming, or the full response string if not streaming.
        """
        # If model loading failed during __init__, yield an error message.
        if self.model is None or self.tokenizer is None:
            yield "Model loading failed during initialization. Check logs for details."
            return

        # --- NEW: Ensure chat history has alternating roles before processing ---
        processed_messages = self._ensure_alternating_roles(messages)
        # ---------------------------------------------------------------------

        # Prepare input messages into tokenized format suitable for the model.
        # Use the processed_messages list
        input_data = self._prepare_input(processed_messages) 
        
        # Move input tensors to GPU if available.
        if torch.cuda.is_available():
            inputs_on_device = {k: v.to('cuda') for k, v in input_data.items()}
        else:
            inputs_on_device = input_data

        # Combine default generation options with any provided in 'options'.
        gen_options = self.options.to_dict() if hasattr(self, 'options') and self.options else {}
        gen_options.update(options)

        # Extract common generation parameters.
        max_new_tokens = gen_options.get('max_new_tokens', 200)
        do_sample = gen_options.get('do_sample', True) 
        top_k = gen_options.get('top_k', 50)
        top_p = gen_options.get('top_p', 0.95)
        temperature = gen_options.get('temperature', 0.7)
        pad_token_id = self.tokenizer.pad_token_id if self.tokenizer.pad_token_id is not None else self.tokenizer.eos_token_id


        if stream:
            # Initialize TextIteratorStreamer to process tokens from the model.
            streamer = TextIteratorStreamer(self.tokenizer, skip_prompt=True, skip_special_tokens=True)
            
            # Define keyword arguments for the model's generate method.
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
            
            # Run model generation in a separate thread to avoid blocking the main thread,
            # allowing tokens to be yielded as they become available.
            thread = threading.Thread(target=self.model.generate, kwargs=generation_kwargs)
            thread.start()

            # Iterate over the streamer to yield each new token as a string.
            for new_token in streamer:
                yield new_token
                # Check for an external close request to stop streaming early.
                if hasattr(self, 'close_requested') and self.close_requested:
                    break 
            
            # Trigger a streaming finished event if the class inherits from Events.
            if isinstance(self, Events):
                self.trigger(self.STREAMING_FINISHED_EVENT)

        else:
            # Non-streaming path: generate the full response at once.
            response_text = self._generate_response(inputs_on_device, gen_options) 
            
            # Trigger a streaming finished event if the class inherits from Events.
            if isinstance(self, Events):
                self.trigger(self.STREAMING_FINISHED_EVENT)
            
            # Yield the full response string once to maintain consistency with the generator interface.
            yield response_text

    def _prepare_input(self, messages: list):
        """
        Formats the list of chat messages into a single input string or tokenized tensor
        that the Hugging Face model can understand.
        """
        # Use tokenizer.apply_chat_template for modern models, which is the recommended way.
        if hasattr(self.tokenizer, "apply_chat_template") and self.tokenizer.apply_chat_template is not None:
            # `tokenize=False` returns the formatted string, which we then tokenize into a tensor.
            # `add_generation_prompt=True` adds the model-specific prompt for an assistant's turn.
            input_string = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = self.tokenizer(input_string, return_tensors="pt")
            return inputs 
        else:
            # Fallback for older models or those without a defined chat template.
            # This is a basic concatenation and might need customization for specific models.
            prepared_messages = []
            # Add system prompt if defined and not already in messages.
            if self.system_prompt and not any(m['role'] == 'system' for m in messages):
                prepared_messages.append(f"System: {self.system_prompt}") 
            
            # Format each message by role and content.
            for msg in messages:
                role = msg.get('role', 'user').capitalize() 
                content = msg.get('content', '')
                prepared_messages.append(f"{role}: {content}")
            
            # Add a clear "Assistant:" prompt to indicate the model's turn to generate.
            if messages and messages[-1].get('role') != 'assistant':
                 prepared_messages.append("Assistant:")

            input_text = "\n".join(prepared_messages)
            
            inputs = self.tokenizer(input_text, return_tensors="pt")
            return inputs

    def _generate_response(self, input_data, options: dict = {}):
        """
        Generates a complete response from the model without streaming.
        """
        if self.model is None or self.tokenizer is None:
            return "Model not loaded." 

        inputs = input_data 

        # Retrieve generation parameters from options, with sensible defaults.
        max_new_tokens = options.get('max_new_tokens', 200)
        do_sample = options.get('do_sample', True)
        top_k = options.get('top_k', 50)
        top_p = options.get('top_p', 0.95)
        temperature = options.get('temperature', 0.7)
        pad_token_id = self.tokenizer.pad_token_id if self.tokenizer.pad_token_id is not None else self.tokenizer.eos_token_id

        # Generate the full sequence.
        outputs = self.model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=do_sample,
            top_k=top_k,
            top_p=top_p,
            temperature=temperature,
            pad_token_id=pad_token_id,
        )
        # Decode the generated token IDs back into a readable string.
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        return response

    def list(self):
        """
        Simulates listing available models. For Hugging Face, this means searching their Hub.
        """
        print("Hugging Face models are available on huggingface.co/models. You can search there for available models.")
        return []

    def pull(self, model_name, stream=True):
        """
        Simulates 'pulling' (downloading and loading) a Hugging Face model.
        """
        print(f"Attempting to 'pull' (download/load) Hugging Face model: {model_name}")
        try:
            # These calls will download the model and tokenizer files to the Hugging Face cache
            # if they are not already present.
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

