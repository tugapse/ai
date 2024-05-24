
"""
This file contains the implementation of an LLM (Large Language Model) bot.
The bot uses the Ollama library to generate responses to user input.
"""

import ollama
from core.events import Events
from .base_llm import BaseModel, ModelParams


class OllamaModel( BaseModel, ModelParams):

    def __init__(self, model, system_prompt=None, host=None):
        """
        Initializes the OllamaModel instance.

        Args:
            model (str): The name of the LLM model to use.
            system_prompt (str, optional): The initial prompt for the bot. Defaults to None.

        Returns:
            None
        """
        super().__init__(model,system_prompt)
        self.server_ip = host
        self.model = ollama.Client(self.server_ip or "127.0.0.1")


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
        new_messages = self.check_system_prompt(messages)

        # if images : self._load_images(images)

        response = self.model.chat(model=self.model_name, messages=new_messages,
                                   stream=stream, options=self.options.to_dict())
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
        return self.model.list()

    def pull(self, model_name, stream=True):
        return self.model.pull(model_name, stream=stream)
