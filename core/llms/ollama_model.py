
"""
This file contains the implementation of an LLM (Large Language Model) bot.
The bot uses the Ollama library to generate responses to user input.
"""

import ollama
from tqdm import tqdm
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
        self.server_ip = host or "127.0.0.1"
        self.model = ollama.Client(self.server_ip )
        self.pull(self.model_name)

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
        
        # load images into context
        if images is not None and len(images) > 0: new_messages.append(super().load_images(images))

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
        if not ":" in model_name:   model_name += ":latest"
        
        models = self.model.list().get("models")
        for model in models:
            if model.get("model") == model_name: return 
        self.__pull_model(model_name, self.model)

    def __pull_model(self,model_name,ollama_inst):
        # Initialize variables: current_digest and bars dictionary                                                                                                                  
        current_digest, bars = '', {}                                                                                                                                               
                                                                                                                                                                                    
        for progress in ollama_inst.pull(model_name, stream=True):                                                                                                                       
            # Extract digest value from each progress item (default to empty string if not present)                                                                                 
            digest = progress.get('digest', '')                                                                                                                                     
                                                                                                                                                                                    
            # If the new digest is different from previous one and it's already tracked                                                                                             
            if digest != current_digest and current_digest in bars:                                                                                                                 
                # Close any existing progress bar for that digest                                                                                                                   
                bars[current_digest].close()                                                                                                                                        
                                                                                                                                                                                    
            # Check if there's no value for this digest (might indicate error or incomplete data)                                                                                   
            if not digest:                                                                                                                                                          
                print(progress.get('status'))  # Print status message from the current progress                                                                                     
                continue                                                                                                                                                            
                                                                                                                                                                                    
            # If it is a new digest: create a new progress bar and update current_digest                                                                                            
            if digest not in bars and (total := progress.get('total')):                                                                                                               
                bars[digest] = tqdm(total=total, desc=f'pulling {digest[7:19]}', unit='B', unit_scale=True)                                                                         
                                                                                                                                                                                    
            # Update the completed portion of this digest's progress bar (if applicable)                                                                                            
            if completed := progress.get('completed'):                                                                                                                              
                bars[digest].update(completed - bars[digest].n)  # n is probably the current value                                                                                  
                                                                                                                                                                                    
            # Set new current_digest for next iteration                                                                                                                             
            current_digest = digest 
