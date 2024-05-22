
from core.events import Events


class ModelParams:
    def __init__(self):
        self.mirostat: int = 0
        self.mirostat_eta: float = 0.0
        self.mirostat_tau: float = 0.0
        self.num_ctx: int = 0
        self.repeat_last_n: int = 0
        self.repeat_penalty: float = 0.0
        self.temperature: float = 0.0
        self.seed: int = 0
        self.stop: str = ""
        self.tf_s_z: float = 0.0
        self.num_predict: int = 0
        self.top_k: int = 0
        self.top_p: float = 0.0


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

        self.options: ModelParams = {
            'num_ctx': BaseModel.CONTEXT_WINDOW_MEDIUM,
            'temperature': 0.5,
            'repeat_penalty': 1.2
        }

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
    

    def list(self):
        raise NotImplementedError("Implement this method")

    def pull(self, model_name, stream=True):
        raise NotImplementedError("Implement this method")

    def stop_stream(self):
        self.close_requested = True
