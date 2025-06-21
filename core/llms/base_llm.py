import threading

class BaseModel:
    CONTEXT_WINDOW_SMALL = 2048
    CONTEXT_WINDOW_MEDIUM = 4096
    CONTEXT_WINDOW_LARGE = 8192
    CONTEXT_WINDOW_XLARGE = 16384
    CONTEXT_WINDOW_HUGE = 32768
    CONTEXT_WINDOW_GIANT = 65536

    STREAMING_FINISHED_EVENT = "streaming_finished"

    def __init__(self, model_name, system_prompt=None):
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.listeners = {} # For event handling
        self.options = {} # Default options

        # Common attributes for graceful interruption
        self.stop_generation_event = threading.Event()
        self._generation_thread = None # Placeholder for potential background thread


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

    def check_system_prompt(self, messages: list):
        """
        Ensures the system prompt is at the beginning of the messages list.
        """
        if self.system_prompt and not any(msg['role'] == 'system' for msg in messages):
            # Use create_message for consistency
            return [BaseModel.create_message("system", self.system_prompt)] + messages
        return messages

    def load_images(self, images: list):
        """
        Placeholder for image loading logic.
        """
        # Implement image loading specific to the model if needed
        # For now, just return a placeholder message or empty dict
        return {"role": "user", "content": "Images provided (content omitted for base model)"}

    # Abstract methods (to be implemented by subclasses)
    def chat(self, messages: list, images: list = None, stream: bool = True, options: object = {}):
        raise NotImplementedError

    def list(self):
        raise NotImplementedError

    def pull(self, model_name, stream=True):
        raise NotImplementedError

    def join_generation_thread(self, timeout: float = None):
        """
        Placeholder for joining the generation thread.
        Subclasses should override this if they use a separate generation thread.
        """
        if self._generation_thread and self._generation_thread.is_alive():
            print("INFO: Waiting for LLM generation thread to finish...")
            self._generation_thread.join(timeout=timeout)
            if self._generation_thread.is_alive():
                print("WARNING: LLM generation thread did not terminate within timeout.")
        self.stop_generation_event.clear() # Always clear the event after potential use

class ModelParams:
    """
    A simple class to hold model parameters.
    """
    def __init__(self):
        self.num_ctx = BaseModel.CONTEXT_WINDOW_LARGE
        self.max_new_tokens = 1024
        self.max_length = 4096
        self.do_sample = True
        self.top_k = 50
        self.top_p = 0.95
        self.temperature = 0.7
        self.quantization_bits = 0 # New: 0 for no quantization, 4 for 4-bit, 8 for 8-bit
        self.enable_thinking = True

    def to_dict(self):
        return {
            "num_ctx": self.num_ctx,
            "max_new_tokens": self.max_new_tokens,
            "max_length": self.max_length,
            "do_sample": self.do_sample,
            "top_k": self.top_k,
            "top_p": self.top_p,
            "temperature": self.temperature,
            "quantization_bits": self.quantization_bits, # Include in dict
            "enable_thinking":self.enable_thinking
        }

