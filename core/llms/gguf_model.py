import os
import threading
import queue
import gc
import sys
import torch # Maintained as per your HuggingFaceModel example

from huggingface_hub import hf_hub_download
from llama_cpp import Llama # Llama is correctly imported from top-level llama_cpp
# LlamaError is not directly importable from llama_cpp or llama_cpp.llama based on your dir() output.
# We will catch generic Exception for llama_cpp errors to ensure compatibility.

from huggingface_hub.errors import RepositoryNotFoundError, GatedRepoError
import requests.exceptions

# Assuming these are available from your project's structure
from core.llms.base_llm import BaseModel, ModelParams
from core.events import Events # Assuming Events class is used for event handling in BaseModel
import functions # Your custom functions module for logging etc.
from color import Color # Your custom Color class


# Define a custom StoppingCriteria to allow external interruption for llama_cpp (conceptual, llama_cpp handles it directly)
class CustomStoppingCriteria:
    """
    Conceptual placeholder for stopping criteria. llama_cpp models directly use `stop` argument.
    """
    def __init__(self, stop_event: threading.Event):
        self.stop_event = stop_event

    def __call__(self, *args, **kwargs) -> bool:
        return self.stop_event.is_set()


# --- GGUFImageLLM Child Class (Implements GGUF model usage) ---
class GGUFImageLLM(BaseModel):
    """
    A child class that extends BaseModel to use a GGUF model for text generation.
    This class integrates with llama-cpp-python to load and interact with GGUF models.
    It can process text descriptions related to images if provided in the prompt.
    """
    def __init__(self,
                 model_name: str,
                 gguf_filename: str,
                 model_repo_id: str = None,
                 system_prompt: str = None,
                 n_gpu_layers: int = 0, # Number of layers to offload to GPU (-1 for all, 0 for none)
                 n_ctx: int = None,   # Context window size, will default to ModelParams.num_ctx if None
                 verbose: bool = False,
                 **kwargs):
        """
        Initializes the GGUFImageLLM.

        Args:
            model_name (str): A descriptive name for your model instance.
            gguf_filename (str): The specific .gguf file name (e.g., 'model.Q4_K_M.gguf').
            model_repo_id (str, optional): The Hugging Face Hub repository ID where the GGUF file
                                           is located (e.g., 'TheBloke/Mixtral-8x7B-Instruct-v0.1-GGUF').
                                           If None, assumes gguf_filename is a local path.
            system_prompt (str, optional): An initial system prompt for the model.
            n_gpu_layers (int): Number of layers to offload to the GPU. Set to -1 to offload all.
                                Defaults to 0 (CPU only).
            n_ctx (int): The context window size for the LLM. If None, uses ModelParams.num_ctx.
            verbose (bool): If True, enables verbose output from the llama_cpp backend.
            **kwargs: Additional arguments to pass to the Llama constructor (e.g., n_threads, etc.).
                      These are stored and passed during model loading.
        """
        functions.debug(f"GGUFImageLLM __init__ called for model: {model_name}")
        super().__init__(model_name, system_prompt=system_prompt)
        self.gguf_filename = gguf_filename
        self.model_repo_id = model_repo_id
        self._n_gpu_layers = n_gpu_layers
        self._n_ctx = n_ctx
        self._verbose = verbose
        self.llama_model = None
        self._llama_init_kwargs = kwargs # Store kwargs to pass to Llama constructor
        self.error_queue = queue.Queue() # Queue to communicate errors from background thread

        # Initialize default model options
        self.options = ModelParams().to_dict()

        try:
            self._load_llm_params()
        except FileNotFoundError as e:
            functions.log(f"ERROR: Model '{self.gguf_filename}' not found. Details: {e}")
            self.llama_model = None
        except Exception as e: # Catch generic Exception for Llama-related errors
            functions.log(f"ERROR: Failed to initialize Llama model for '{self.model_name}'. Details: {e}")
            self.llama_model = None
            import traceback
            functions.log(f"Traceback:\n{traceback.format_exc()}")


    def _load_llm_params(self):
        """Internal method to load the GGUF model from Hugging Face Hub or local path."""
        functions.log(f"Attempting to load GGUF model: {self.model_name}...")
        
        effective_n_ctx = self._n_ctx if self._n_ctx is not None else self.options.get("num_ctx", BaseModel.CONTEXT_WINDOW_LARGE)

        if self.model_repo_id and self.gguf_filename:
            try:
                functions.log(f"Attempting to load via Llama.from_pretrained from {self.model_repo_id} / {self.gguf_filename}...")
                self.llama_model = Llama.from_pretrained(
                    repo_id=self.model_repo_id,
                    filename=self.gguf_filename,
                    n_gpu_layers=self._n_gpu_layers,
                    n_ctx=effective_n_ctx,
                    verbose=self._verbose,
                    **self._llama_init_kwargs
                )
                functions.log(f"GGUF model '{self.model_name}' loaded successfully via from_pretrained!")
                return # Model loaded, exit
            except (RepositoryNotFoundError, GatedRepoError, requests.exceptions.RequestException) as e:
                functions.log(f"WARNING: Llama.from_pretrained failed (likely download/access issue): {e}. Falling back to local check.")
            except Exception as e:
                functions.log(f"WARNING: Llama.from_pretrained encountered unexpected error: {e}. Falling back to local check.")
                import traceback
                functions.log(f"Traceback:\n{traceback.format_exc()}")

        # Fallback to local path or hf_hub_download if from_pretrained didn't work or wasn't used
        model_path = None
        if os.path.exists(self.gguf_filename):
            model_path = self.gguf_filename
            functions.log(f"Loading model from local path: {model_path}")
        elif self.model_repo_id and self.gguf_filename: # If model_repo_id and filename still exist, try hf_hub_download directly
            try:
                functions.log(f"Attempting direct hf_hub_download for {self.gguf_filename} from {self.model_repo_id}...")
                model_path = hf_hub_download(
                    repo_id=self.model_repo_id,
                    filename=self.gguf_filename
                )
                functions.log(f"Model downloaded to: {model_path} via hf_hub_download.")
            except (RepositoryNotFoundError, GatedRepoError, requests.exceptions.RequestException) as e:
                functions.log(f"ERROR: Error downloading model from Hugging Face Hub with hf_hub_download: {e}.")
            except Exception as e:
                functions.log(f"ERROR: An unexpected error occurred during hf_hub_download: {e}.")
                import traceback
                functions.log(f"Traceback:\n{traceback.format_exc()}")
        
        if not model_path:
            raise FileNotFoundError(
                f"GGUF model '{self.gguf_filename}' not found locally and "
                f"could not be downloaded from '{self.model_repo_id}' (if provided)."
            )

        # If we reached here, model_path should be set from local or hf_hub_download
        try:
            self.llama_model = Llama(
                model_path=model_path,
                n_gpu_layers=self._n_gpu_layers,
                n_ctx=effective_n_ctx,
                verbose=self._verbose,
                **self._llama_init_kwargs
            )
            functions.log(f"GGUF model '{self.model_name}' loaded successfully!")
        except Exception as e: # Catch generic Exception
            raise Exception(f"Failed to initialize llama_cpp model: {e}")

    def _format_messages_to_prompt(self, messages: list) -> str:
        """
        Formats a list of messages into a single string prompt suitable for the GGUF model.
        This uses a basic chat template. For specific models, a more advanced template
        (e.g., Llama-2-chat, Alpaca) might be necessary.
        """
        processed_messages = self.check_system_prompt(messages)
        
        formatted_prompt = ""
        for message in processed_messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            
            # Simple prompt formatting. Adapt this for specific GGUF models (e.g., Llama, Mistral)
            # based on their recommended chat templates.
            if role == "system":
                formatted_prompt += f"<<SYS>>\n{content}\n<</SYS>>\n\n"
            elif role == "user":
                formatted_prompt += f"[INST] {content} [/INST]"
            elif role == "assistant":
                formatted_prompt += f" {content} " # Assistant's previous response
            formatted_prompt += "\n" 
        
        return formatted_prompt.strip()

    def _generate_in_thread(self, prompt: str, generation_options: dict, output_queue: queue.Queue):
        """
        Target function for the generation thread.
        Handles model generation and puts tokens into the output_queue.
        Puts any caught exceptions into the error_queue.
        """
        functions.debug("_generate_in_thread started for GGUF model.")
        try:
            # Map ModelParams options to llama_cpp.Llama.create_completion arguments
            llama_params = {
                "max_tokens": generation_options.get("max_new_tokens", 200),
                "temperature": generation_options.get("temperature", 0.7),
                "top_k": generation_options.get("top_k", 50),
                "top_p": generation_options.get("top_p", 0.95),
                "presence_penalty": generation_options.get("presence_penalty", 0.0),
                "frequency_penalty": generation_options.get("frequency_penalty", 0.0),
                "stop": ["<|im_end|>", "</s>", "```"], # Common stop sequences
                "echo": False # Do not echo the prompt in the output
            }

            functions.debug(f"_generate_in_thread calling llama_model.create_completion with params: {llama_params}")
            stream_iter = self.llama_model.create_completion(prompt, stream=True, **llama_params)
            
            full_response_content = ""
            for chunk in stream_iter:
                if self.stop_generation_event.is_set():
                    functions.log("INFO: Generation stopped by user request.")
                    break
                
                delta = chunk["choices"][0]["text"]
                full_response_content += delta
                output_queue.put(delta) # Put token into the queue for yielding

            output_queue.put(None) # Signal end of stream
            self.trigger(BaseModel.STREAMING_FINISHED_EVENT, full_response_content) # Trigger event for full response
            functions.debug("_generate_in_1thread llama_model.create_completion completed (Streaming).")

        except Exception as e: # Catch generic Exception
            import traceback
            error_message = f"CRITICAL ERROR: An unexpected error occurred during GGUF model generation: {e}"
            error_message += f"\nTraceback:\n{traceback.format_exc()}"
            functions.log(error_message)
            self.error_queue.put(error_message)
            output_queue.put(None) # Ensure stream terminates
        finally:
            self.stop_generation_event.clear()
            functions.debug("_generate_in_thread finally block executed. Clearing stop event.")


    def join_generation_thread(self, timeout: float = None):
        """
        Waits for the background generation thread to complete.
        Overrides BaseModel's method.
        """
        super().join_generation_thread(timeout) # Calls BaseModel's join_generation_thread
        # Additionally, clear CUDA cache if applicable, similar to HuggingFaceModel
        # Note: llama_cpp handles its own CUDA memory. `torch.cuda.empty_cache()`
        # might not directly apply here if llama_cpp is not using PyTorch's CUDA context.
        # However, for consistency with HuggingFaceModel, including similar cleanup.
        if torch.cuda.is_available(): # Check if CUDA is available before attempting
            functions.debug("Clearing CUDA cache after GGUF generation thread join (if CUDA is used by llama_cpp).")
            # A direct equivalent for llama_cpp might involve its internal APIs if exposed.
            gc.collect() 


    def chat(self, messages: list, images: list = None, stream: bool = True, options: object = None):
        """
        Generates a chat response from the GGUF model.
        When 'stream' is True, generation happens in a separate thread and yields tokens as they are generated.
        When 'stream' is False, generation happens in the main thread and yields the full response.
        """
        functions.debug(f"GGUFImageLLM chat() called. Stream: {stream}")

        if self.llama_model is None:
            error_msg = "GGUF model not loaded during initialization. Check logs for details."
            functions.log(f"ERROR: {error_msg}")
            if stream:
                yield error_msg
            return error_msg

        self.stop_generation_event.clear()
        # Ensure error_queue is empty from previous runs
        while not self.error_queue.empty():
            self.error_queue.get()

        functions.debug("Chat method initialized, queues cleared.")

        # Handle images if provided - assume text descriptions are added to messages
        if images:
            image_message = self.load_images(images) # This method just logs and returns placeholder
            if image_message:
                # Append image message to the last user message or as a new user message
                last_user_message_index = -1
                for i in reversed(range(len(messages))):
                    if messages[i]['role'] == 'user':
                        messages[i]['content'] += f"\n{image_message['content']}"
                        break
                else: # No user message found, add as a new one
                    messages.append(image_message)

        processed_messages = self._format_messages_to_prompt(messages) # Format all messages into a single prompt string

        processed_messages_log = ""
        if processed_messages:
            processed_messages_log = processed_messages[:50].replace("\n", "\\n")
        else:
            processed_messages_log = "[No messages to process]"
        functions.debug(f"Formatted prompt preview: '{processed_messages_log}'...")

        # Update options if provided, otherwise use current self.options
        current_options = self.options.copy()
        current_options.update(options)

        max_new_tokens = current_options.get("max_new_tokens", 200) # Default for GGUF here
        temperature = current_options.get("temperature", 0.7)
        top_k = current_options.get("top_k", 50)
        top_p = current_options.get("top_p", 0.95)
        
        # Corrected Color.END to Color.RESET
        text = f"Generation options: max_new_tokens={max_new_tokens}, temperature={temperature}, top_k={top_k}, top_p={top_p}"
        functions.debug(Color.GREEN + text + Color.RESET)


        if stream:
            functions.debug("Entering streaming (threaded) generation path for GGUF model.")
            output_queue = queue.Queue()
            self._generation_thread = threading.Thread(
                target=self._generate_in_thread,
                args=(processed_messages, current_options, output_queue)
            )
            self._generation_thread.start()
            functions.debug(f"Generation thread started ({self._generation_thread.name}). Starting to yield tokens from queue...")

            while True:
                try:
                    token = output_queue.get(timeout=0.1) # Short timeout to allow main thread to check stop_event
                    if token is None: # Signal for end of stream
                        break
                    yield token
                except queue.Empty:
                    if not self._generation_thread.is_alive() and self.error_queue.empty():
                        # Thread has finished and no error, so queue is truly empty and stream is done
                        break
                    if self.stop_generation_event.is_set():
                        functions.log("INFO: Main thread detected stop event during streaming.")
                        break # Exit if stop requested
                    continue # Continue waiting for tokens

                if not self.error_queue.empty():
                    error_message = self.error_queue.get()
                    functions.log(f"ERROR: Error received from generation thread during streaming: {error_message}")
                    # Re-raise or yield error to the consumer, depending on desired behavior
                    yield f"\nERROR: {error_message}"
                    break # Stop yielding on error
            functions.out("\n") # Newline after streamed output
            functions.debug("GGUF Streamer finished yielding all tokens.")

            if not self.error_queue.empty():
                error_message = self.error_queue.get()
                functions.log(f"ERROR: Error received from generation thread after streaming: {error_message}")
                # This error might have caused the stream to end prematurely, yield if not already handled
                yield f"\nERROR: {error_message}"

        else: # Non-streaming path
            functions.debug("Entering non-streaming (synchronous) generation path for GGUF model.")
            try:
                response_text = self._generate_response_sync(processed_messages, current_options)
                functions.debug(f"Synchronous GGUF generation complete. Output length: {len(response_text)}. Yielding...")

                # In non-streaming, the "finished" event can be triggered immediately after response
                self.trigger(BaseModel.STREAMING_FINISHED_EVENT, response_text)
                yield response_text
            except Exception as e: # Catch generic Exception
                error_message = (
                    f"ERROR: GGUF model generation failed. "
                    f"This often indicates an issue with model execution or parameters."
                    f"\nDetails: {e}"
                )
                functions.log(error_message)
                import traceback
                functions.log(f"Traceback:\n{traceback.format_exc()}")
                yield error_message


    def _generate_response_sync(self, prompt: str, options: dict = {}):
        """Generates a complete response without streaming (used by non-threaded path)."""
        if self.llama_model is None: # Corrected `== None` to `is None`
            return "GGUF model not loaded."

        # Map ModelParams options to llama_cpp.Llama.create_completion arguments
        llama_params = {
            "max_tokens": options.get("max_new_tokens", 200),
            "temperature": options.get("temperature", 0.7),
            "top_k": options.get("top_k", 50),
            "top_p": options.get("top_p", 0.95),
            "presence_penalty": options.get("presence_penalty", 0.0),
            "frequency_penalty": options.get("frequency_penalty", 0.0),
            "stop": ["<|im_end|>", "</s>", "```"],
            "echo": False
        }

        functions.debug(f"_generate_response_sync calling llama_model.create_completion with params: {llama_params}")

        output = self.llama_model.create_completion(prompt, stream=False, **llama_params)
        
        response_text = output["choices"][0]["text"]

        escaped_response_chunk = response_text[:100].replace("\n", "\\n")
        functions.debug(f"_generate_response_sync decoded text length: {len(response_text)}. First 100 chars: '{escaped_response_chunk}'")

        return response_text

    def list(self) -> list:
        """
        Lists information about the currently loaded GGUF model.
        Mimics HuggingFaceModel's approach of logging and returning empty list if no specific local list.
        """
        functions.log(
            "GGUF models are typically loaded from local files or Hugging Face Hub. "
            "This list method shows info for the currently loaded model."
        )
        if self.llama_model:
            model_info = {
                "name": self.model_name,
                "gguf_filename": self.gguf_filename,
                "repo_id": self.model_repo_id,
                "n_ctx": self.llama_model.n_ctx(),
                "n_gpu_layers": self.llama_model.n_gpu_layers(),
                "type": "GGUF"
            }
            return [model_info]
        return []

    def pull(self, model_name_or_repo_id: str, gguf_filename: str = None, stream: bool = True):
        """
        Pulls (downloads) a GGUF model from Hugging Face Hub.
        Mimics HuggingFaceModel's generator return for streaming.

        Args:
            model_name_or_repo_id (str): The Hugging Face Hub repository ID (e.g., 'TheBloke/Mixtral-8x7B-Instruct-v0.1-GGUF').
            gguf_filename (str, optional): The specific .gguf file name to download. Required if pulling.
            stream (bool): If True, yields status messages during download.
        """
        functions.log(f"Attempting to 'pull' (download) GGUF model: {model_name_or_repo_id} / {gguf_filename}")

        if not gguf_filename:
            error_message = "ERROR: GGUF filename must be provided to pull a specific GGUF model."
            functions.log(error_message)
            if stream:
                yield error_message
            return error_message if not stream else None

        try:
            message_start = f"Downloading '{gguf_filename}' from '{model_name_or_repo_id}'..."
            functions.log(message_start)
            if stream:
                yield message_start

            downloaded_path = hf_hub_download(
                repo_id=model_name_or_repo_id,
                filename=gguf_filename
            )
            message_success = f"Model '{gguf_filename}' downloaded successfully to: {downloaded_path}"
            functions.log(message_success)
            if stream:
                yield message_success
            return downloaded_path

        except Exception as e:
            error_message = f"Error 'pulling' model {model_name_or_repo_id}/{gguf_filename}: {e}"
            functions.log(f"ERROR: {error_message}")
            if stream:
                yield error_message
            return error_message if not stream else None
