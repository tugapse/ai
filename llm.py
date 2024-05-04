import ollama

import tools
from chat import ChatRoles
from events import Events


class LLMBot(Events):

    STREAMING_FINISHED_EVENT = "streaming_finished"
    STREAMING_TOKEN_EVENT = "streaming_token"
    
    def __init__(self, model,system_prompt=None): 
        super().__init__()
        self.model_name = model
        self.system_prompt = system_prompt

    def chat(self, messages:list, stream=True): 
        new_messages = self.check_system_prompt(messages)
        response = ollama.chat(model=self.model_name, messages=new_messages,stream=stream) 
        if stream:
            for chunks in response:
                yield chunks[ 'message' ][ 'content' ] 
            self.trigger(self.STREAMING_FINISHED_EVENT)

        else:
            self.trigger(self.STREAMING_FINISHED_EVENT)
            yield response


    def check_system_prompt(self,messages:list):
        if ChatRoles.SYSTEM not in [obj['role'] for obj in messages]:
            messages.insert(0,{'role':ChatRoles.SYSTEM,'content':self.system_prompt})
        return messages
    
    def create_message(self, role:ChatRoles, message:str):
        return {'role':role,'content':message}

    
