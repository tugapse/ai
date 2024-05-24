
from core.events import Events


class ModelParams:
    """
    Parameters for controlling the behavior of the model.
    
    Attributes:
        mirostat (int): Enable Mirostat sampling for controlling perplexity.
            (default: 0, 0 = disabled, 1 = Mirostat, 2 = Mirostat 2.0)
        mirostat_eta (float): Influences how quickly the algorithm responds to feedback from the generated text.
            A lower learning rate will result in slower adjustments, while a higher learning rate will make the
            algorithm more responsive. (Default: 0.1)
        mirostat_tau (float): Controls the balance between coherence and diversity of the output.
            A lower value will result in more focused and coherent text. (Default: 5.0)
        num_ctx (int): Sets the size of the context window used to generate the next token. (Default: 2048)
        repeat_last_n (int): Sets how far back for the model to look back to prevent repetition.
            (Default: 64, 0 = disabled, -1 = num_ctx)
        repeat_penalty (float): Sets how strongly to penalize repetitions.
            A higher value (e.g., 1.5) will penalize repetitions more strongly,
            while a lower value (e.g., 0.9) will be more lenient. (Default: 1.1)
        temperature (float): The temperature of the model.
            Increasing the temperature will make the model answer more creatively. (Default: 0.8)
        seed (int): Sets the random number seed to use for generation.
            Setting this to a specific number will make the model generate the same text for the same prompt. (Default: 0)
        stop (str): Sets the stop sequences to use.
            When this pattern is encountered, the LLM will stop generating text and return.
            Multiple stop patterns may be set by specifying multiple separate stop parameters in a modelfile.
        tf_s_z (float): Tail free sampling is used to reduce the impact of less probable tokens from the output.
            A higher value (e.g., 2.0) will reduce the impact more, while a value of 1.0 disables this setting. (default: 1)
        num_predict (int): Maximum number of tokens to predict when generating text.
            (Default: 128, -1 = infinite generation, -2 = fill context)
        top_k (int): Reduces the probability of generating nonsense.
            A higher value (e.g. 100) will give more diverse answers,
            while a lower value (e.g. 10) will be more conservative. (Default: 40)
        top_p (float): Works together with top-k.
            A higher value (e.g., 0.95) will lead to more diverse text,
            while a lower value (e.g., 0.5) will generate more focused and conservative text. (Default: 0.9)
    """
    def __init__(self):
        """
        Initializes the ModelParams object with default values.
        """
        self.mirostat: int = None
        self.mirostat_eta: float = None
        
        self.mirostat_tau: float = None
        
        self.num_ctx: int = None
        self.repeat_last_n: int = None
        self.repeat_penalty: float = None
        
        self.temperature: float = None
        
        self.seed: int = None
        self.stop: str = None
        self.tf_s_z: float = None
        
        self.num_predict: int = None
        self.top_k: int = None
        self.top_p: float = None
        
    
    def to_dict(self):
        """
        Converts the ModelParams object to a dictionary.
        Returns:
            dict: A dictionary representation of the ModelParams attributes.
        """
        return self.__dict__


class BaseModel(Events):

    ROLE_USER: str = "user"
    ROLE_ASSISTANT: str = "assistant"
    ROLE_SYSTEM: str = "system"

    STREAMING_FINISHED_EVENT = "streaming_finished"
    STREAMING_TOKEN_EVENT = "streaming_token"

    CONTEXT_WINDOW_SMALL = 2048
    CONTEXT_WINDOW_MEDIUM = 4096
    CONTEXT_WINDOW_LARGE = 8192
    CONTEXT_WINDOW_EXTRA_LARGE = 16384

    def __init__(self, model, system_prompt=None, **kargs):
        """
        Initializes the OllamaModel instance.

        Args:
            model (str): The name of the LLM model to use.
            system_prompt (str, optional): The initial prompt for the bot. Defaults to None.

        Returns:
            None
        """
        super().__init__()
        self.model_name = model
        self.system_prompt = system_prompt
        self.model = None
        self.close_requested = False

        self.options: ModelParams = ModelParams()
    
    def _load_llm_params(self):
        pass

   
    def check_system_prompt(self, messages: list):
        """
        This method checks if the system prompt is present in the messages.

        Args:
            messages (list): A list of message objects.

        Returns:
            list: The updated list of messages.
        """
        if self.ROLE_SYSTEM not in [obj['role'] for obj in messages]:
            messages.insert(0, {'role': self.ROLE_SYSTEM,
                            'content': self.system_prompt})
        return messages

    def stop_stream(self):
        self.close_requested = True

    @classmethod
    def create_message(self, role: str, message: str) -> dict[str, str]:
        """
        This method creates a new message object.

        Args:
            role (ChatRoles): The role of the message.
            message (str): The content of the message.

        Returns:
            dict: A dictionary representing the message.
        """
        return {'role': role, 'content': message}
    
    def chat(self, messages: list, images:list[str] = None, stream: bool = True, options: object = {}):
        """
        This method allows the bot to chat with users.

        Args:
            messages (list): A list of message objects.
            stream (bool, optional): Whether to stream the responses or not. Defaults to True.
            options (dict, optional): Additional options for the LLM model. Defaults to {}.

        Returns:
            None
        """
        raise NotImplementedError("Implement this method")

    def list(self):
        raise NotImplementedError("Implement this method")

    def pull(self, model_name, stream=True):
        raise NotImplementedError("Implement this method")

    def load_images(self, images ):
        message = BaseModel.create_message(BaseModel.ROLE_USER, f"Loaded image filenames:\n{str(images)}")  
        message['images'] = images
        return message
