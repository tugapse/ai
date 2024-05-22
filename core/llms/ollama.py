
"""
This file contains the implementation of an LLM (Large Language Model) bot.
The bot uses the Ollama library to generate responses to user input.
"""

import ollama
from core.events import Events
from core.llms.llm import BaseModel


class OllamaModel(Events,BaseModel):

    ROLE_USER: str = "user"
    ROLE_ASSISTANT: str = "assistant"
    ROLE_SYSTEM: str = "system"

    STREAMING_FINISHED_EVENT = "streaming_finished"
    STREAMING_TOKEN_EVENT = "streaming_token"

    CONTEXT_WINDOW_SMALL = 2048
    CONTEXT_WINDOW_MEDIUM = 4096
    CONTEXT_WINDOW_LARGE = 8192
    CONTEXT_WINDOW_EXTRA_LARGE = 16384

    def __init__(self, model, system_prompt=None, host=None):
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
        self.server_ip = host
        self.model = ollama.Client(self.server_ip) if self.server_ip else None
        self.close_requested = False
        self.options = {
            'num_ctx': 16384,   # Default: 2048
            'temperature': 0.5,
            'repeat_penalty': 1.2
        }

    def chat(self, messages: list, stream: bool = True, options: object = {}):
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

        response = None
        chat_func = None
        if self.model:
            chat_func = self.model.chat
        else:
            chat_func = ollama.chat

        response = chat_func(model=self.model_name, messages=new_messages,
                             stream=stream, options=self.options)
        if stream:
            for chunks in response:
                yield chunks['message']['content']
                if self.close_requested:
                    response.close()
                    self.close_requested = False
            self.trigger(self.STREAMING_FINISHED_EVENT)

        else:
            self.trigger(self.STREAMING_FINISHED_EVENT)
            return response

    def list(self):
        if self.model:
            return self.model.list()
        else:
            return ollama.list()

    def pull(self, model_name, stream=True):
        if self.model:
            return self.model.pull(model_name, stream=True)
        else:
            return ollama.pull(model_name, stream=True)