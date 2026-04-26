import os
import gc
import threading
import functions
from entities.model_enums import InferenceBackend

class TokenCountInfo:
    def __init__(self) -> None:
        self.prompt_count = 0
        self.max_context_window = 0
        self.max_output_tokens = 0
        self.total_prompt_count = 0 
        self.printed_tokens_count = 0
    
    def get_log_string(self) -> str:
        """Returns a condensed 'fuel gauge' of the current token state."""
        # Calculate usage percentage for the log
        usage = (self.total_prompt_count / (self.max_context_window-self.max_output_tokens) * 100) if self.max_context_window > 0 else 0
        return (
            f"Tokens: [P: {self.prompt_count} | T: {self.total_prompt_count} | Out: {self.printed_tokens_count}] "
            f"Window: {self.max_context_window-self.max_output_tokens} ({usage:.1f}%)"
        )
class BaseModel:
    CONTEXT_WINDOW_SMALL = 2048
    CONTEXT_WINDOW_MEDIUM = 4096
    CONTEXT_WINDOW_LARGE = 8192
    CONTEXT_WINDOW_XLARGE = 16384
    CONTEXT_WINDOW_HUGE = 32768
    CONTEXT_WINDOW_GIANT = 65536
    CONTEXT_WINDOW_128K = 128748
    CONTEXT_WINDOW_256K = 262144
    CONTEXT_WINDOW_1M = 1048576
    CONTEXT_WINDOW_2M = 2097152

    STREAMING_FINISHED_EVENT = "streaming_finished"

    def __init__(self, model_name, system_prompt=None, override_system_by_user_template=False, **kargs):
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.listeners = {} # For event handling
        self.options = {} # Default options
        self.tokenizer = None
        self.override_system_by_user_template = override_system_by_user_template
        
        # Common attributes for graceful interruption
        self.stop_generation_event = threading.Event()
        self._generation_thread = None # Placeholder for potential background thread
        self.inference_device = InferenceBackend.CPU # Default to CPU, lazy-load torch for GPU check
        self.token_info_count = TokenCountInfo()


    def init_pytorch_cuda(self):
        try:
            import torch
            if torch.cuda.is_available():
                self.inference_device = InferenceBackend.GPU_CUDA
                functions.log("PyTorch CUDA available. Set inference device to GPU.")
            else:
                functions.log("PyTorch CUDA not available. Using CPU.")
        except ImportError:
            functions.log("PyTorch not found. Using CPU.")
            pass

    def _prepare_input(self, messages: list):
        """
        Formats chat messages into model input, ensuring the last turn is for the assistant to generate.
        This handles models with and without `apply_chat_template`.
        """
        if self.system_prompt and not any(m["role"] == "system" for m in messages):
                messages.insert(0, BaseModel.create_message("system", self.system_prompt))
        if (
            hasattr(self.tokenizer, "apply_chat_template")
            and self.tokenizer.apply_chat_template is not None
        ):
            input_string = self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            inputs = self.tokenizer(input_string, return_tensors="pt")
            functions.debug(
                f"_prepare_input using apply_chat_template. Input string length: {len(input_string)}"
            )
            return inputs
        else:
            prepared_messages = []
            if self.system_prompt and not any(m["role"] == "system" for m in messages):
                prepared_messages.append(
                    BaseModel.create_message("system", self.system_prompt)
                )

            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                prepared_messages.append(BaseModel.create_message(role, content))

            input_text = ""
            for msg in prepared_messages:
                if msg["role"] == "system":
                    input_text += f"System: {msg['content']}\n"
                elif msg["role"] == "user":
                    input_text += f"User: {msg['content']}\n"
                elif msg["role"] == "assistant":
                    input_text += f"Assistant: {msg['content']}\n"

            if messages and messages[-1]["role"] == "user":
                input_text += "Assistant:"

            inputs = self.tokenizer(input_text, return_tensors="pt")
            functions.debug(
                f"_prepare_input using manual formatting. Input text length: {len(input_text)}"
            )
            return inputs

    def add_event(self, event_name, listener):
        if event_name not in self.listeners:
            self.listeners[event_name] = []
        self.listeners[event_name].append(listener)

    def trigger(self, event_name, data=None):
        if event_name in self.listeners:
            for listener in self.listeners[event_name]:
                listener(data)

    @staticmethod
    def create_message(role: str, content: str) -> dict:
        """
        Creates a message dictionary in the format expected by LLMs.
        
        Args:
            role (str): The role of the message sender (e.g., 'user', 'assistant', 'system').
            content (str): The text content of the message.
        
        Returns:
            dict: A dictionary representing the message.
        """
        return {'role': role, 'content': content}
   
    def get_system_info(self)-> str:

        system_info = functions.get_system_info_prompt_concise()

        current_time_str = system_info.get("time", "Unknown Time")
        os_info = system_info.get("os", "Unknown OS")

        return f"System Context: (Time: {current_time_str} | OS: {os_info})"
    
    def check_system_prompt(self, messages: list):
        """
        Ensures the system prompt is at the beginning of the messages list,
        updated with real-time system context information obtained as an object.
        """

        enriched_system_info_prefix = self.get_system_info()

        final_system_prompt_content = enriched_system_info_prefix
        if self.system_prompt:
            final_system_prompt_content += f"\n{self.system_prompt}"

        filtered_messages = [
            msg for msg in messages
            if not (msg['role'] == "system" or msg.get('original_role') == "system")
        ]


        updated_messages = [BaseModel.create_message("system", final_system_prompt_content)] + filtered_messages

        if self.override_system_by_user_template:
            for msg in updated_messages:
                if msg['role'] == "system":
                    msg['role'] = "user"
                    msg['original_role'] = "system" # Mark it as originally a system message


        return updated_messages


    def load_images(self, images: list):
        """
        Placeholder for image loading logic.
        """
        # Implement image loading specific to the model if needed
        # For now, just return a placeholder message or empty dict
        return {"role": "user", "content": "Images provided (content omitted for base model)"}

    def join_generation_thread(self, timeout: float = None):
        """
        Placeholder for joining the generation thread.
        Subclasses should override this if they use a separate generation thread.
        """
        if self._generation_thread and self._generation_thread.is_alive():
            functions.log("INFO: Waiting for LLM generation thread to finish...")
            self._generation_thread.join(timeout=timeout)
            if self._generation_thread.is_alive():
                functions.log("WARNING: LLM generation thread did not terminate within timeout.")
        self.stop_generation_event.clear() # Always clear the event after potential use
    
    # Abstract methods (to be implemented by subclasses)
    def chat(self, messages: list, images: list = None, stream: bool = True, options: object = {}):
        raise NotImplementedError

    def generate_structured(self, messages: list, schema: object, images: list = None, options: object = {}):
        """
        Generates a structured output based on a provided schema (e.g., Pydantic model).
        Subclasses must implement this to support structured data generation.
        """
        raise NotImplementedError

    def list(self):
        raise NotImplementedError

    def pull(self, model_name, stream=True):
        raise NotImplementedError

    def is_gpu_available(self):
        if self.inference_device == InferenceBackend.GPU_CUDA:
            try:
                import torch
                return torch.cuda.is_available()
            except ImportError:
                return False
        elif self.inference_device == InferenceBackend.GPU_AMD:
            # TODO add implentations here for direct_ml and override in gguf
            return False
        return False
    
    def clean_cache(self):
        functions.debug("Clearing cache")
        if self.is_gpu_available():
            try:
                import torch
                torch.cuda.empty_cache()
            except ImportError:
                functions.log("PyTorch not available, cannot clear CUDA cache.")
        gc.collect()
    
    def getTokenCount(self,**kargs):
        functions.debug("Implement getPromptTokens method in subclass")
        return self.token_info_count
    
    def request_shutdown(self):
        self.stop_generation_event.set()
        self.join_generation_thread(2)
        self.clean_cache()
    
    def unload(self):
        functions.error("Subclasses should implement the unload method to clear model resources.")

class ModelParams:
    """
    A simple class to hold model parameters.
    """
    def __init__(self, **kargs):
        self.num_ctx = kargs.get('num_ctx') or BaseModel.CONTEXT_WINDOW_LARGE
        self.max_new_tokens = kargs.get('max_new_tokens', 2048)
        self.max_length =kargs.get('max_length', 4096)
        self.do_sample = kargs.get('do_sample', True)
        self.top_k = kargs.get('top_k', 50)
        self.top_p =kargs.get('top_p', 0.95)
        self.temperature = kargs.get('temperature',0.5)
        self.quantization_bits = kargs.get('quantization_bits',0)  # New: 0 for no quantization, 4 for 4-bit, 8 for 8-bit
        self.enable_thinking = kargs.get('enable_thinking',True)
        self.presence_penalty = kargs.get('presence_penalty', 1.0)
        self.frequency_penalty = kargs.get('frequency_penalty', 1.0)
        self.use_system_prompt = kargs.get('use_system_prompt', True)
        self.inference_backend :InferenceBackend = InferenceBackend.CPU
        self.format = kargs.get('format', None) # New: for structured output, e.g., 'json'

    def to_dict(self):
        """Converts the parameters to a dictionary, excluding None values for format."""
        d = {
            "num_ctx": self.num_ctx,
            "max_new_tokens": self.max_new_tokens,
            "max_length": self.max_length,
            "do_sample": self.do_sample,
            "top_k": self.top_k,
            "top_p": self.top_p,
            "temperature": self.temperature,
            "quantization_bits": self.quantization_bits,
            "enable_thinking":self.enable_thinking,
            "presence_penalty":self.presence_penalty,
            "frequency_penalty":self.frequency_penalty,
            "use_system_prompt":self.use_system_prompt
        }
        if self.format:
            d['format'] = self.format
        return d
    

