
"""
This file contains the implementation of an LLM (Large Language Model) bot.
The bot uses the Ollama library to generate responses to user input.
"""

import ollama
from ai.color import Color, format_text, pformat_text
from ai.core.chat import ChatRoles
from ai.core.events import Events

class LLMBot(Events):
    """
    This class represents an LLM bot. It inherits from the Events class and provides methods for chatting with users.
    """

    STREAMING_FINISHED_EVENT = "streaming_finished"
    STREAMING_TOKEN_EVENT = "streaming_token"

    
    CONTEXT_WINDOW_SMALL = 2048
    CONTEXT_WINDOW_MEDIUM = 4096
    CONTEXT_WINDOW_LARGE = 8192
    CONTEXT_WINDOW_EXTRA_LARGE = 16384

    def __init__(self, model, system_prompt=None): 
        """
        Initializes the LLMBot instance.

        Args:
            model (str): The name of the LLM model to use.
            system_prompt (str, optional): The initial prompt for the bot. Defaults to None.

        Returns:
            None
        """
        super().__init__()
        self.model_name = model
        self.system_prompt = system_prompt

        # Ollama Options Documentation
        # -> https://github.com/ollama/ollama/blob/main/docs/modelfile.md#parameter
        self.llm_options_params_type = {
            'mirostat': int,
            'mirostat_eta': float,
            'mirostat_tau': float,
            'num_ctx': int,
            'repeat_last_n': int,
            'repeat_penalty': float,
            'temperature': float,
            'seed': int,
            'stop': str,
            'tf_s_z': float,
            'num_predict': int,
            'top_k': int,
            'top_p': float
        }
        self.llm_options = {
            'num_ctx': 16384,   # Default: 2048
            'temperature':0.5,
            'repeat_penalty':1.2
        }

    def chat(self, messages:list, stream:bool=True, options:object = {}):
        """
        This method allows the bot to chat with users.

        Args:
            messages (list): A list of message objects.
            stream (bool, optional): Whether to stream the responses or not. Defaults to True.
            options (dict, optional): Additional options for the LLM model. Defaults to {}.

        Returns:
            None
        """
        new_messages = self.check_system_prompt(messages)

        request_options = self.llm_options.copy()
        request_options.update(options)
        request_options_cleaner = []

        # Validate Used Options
        for key, value in request_options.items():
            if key not in self.llm_options_params_type:
                request_options_cleaner.append(key)
                print(f"{Color.YELLOW}# LLM Chat Option '{key}' is an invalid option so it has been removed from request options")
            elif not isinstance(value, self.llm_options_params_type[key]):
                request_options_cleaner.append(key)
                print(f"{Color.YELLOW}# LLM Chat Option '{key}' should be of type ({self.llm_options_params_type[key].__name__}) and type ({type(value).__name__}) was given so it has been removed from request options")

        for key in request_options_cleaner:
            del request_options[key]
        print(f"{Color.RESET}", end="")
        response = ollama.chat(model=self.model_name, messages=new_messages, stream=stream, options=request_options)

        if stream:
            for chunks in response:
                yield chunks['message']['content']
            self.trigger(self.STREAMING_FINISHED_EVENT)

        else:
            self.trigger(self.STREAMING_FINISHED_EVENT)
            yield response

    def check_system_prompt(self,messages:list):
        """
        This method checks if the system prompt is present in the messages.

        Args:
            messages (list): A list of message objects.

        Returns:
            list: The updated list of messages.
        """
        if ChatRoles.SYSTEM not in [obj['role'] for obj in messages]:
            messages.insert(0, {'role':ChatRoles.SYSTEM,'content':self.system_prompt})
        return messages

    def create_message(self, role:ChatRoles, message:str):
        """
        This method creates a new message object.

        Args:
            role (ChatRoles): The role of the message.
            message (str): The content of the message.

        Returns:
            dict: A dictionary representing the message.
        """
        return {'role':role,'content':message}