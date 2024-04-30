import ollama

from events import Events

class LLMbot(Events):

    STREAMING_FINISHED_EVENT = "streaming_finished"
    STREAMING_TOKEN_EVENT = "streaming_token"
    
    def __init__(self, model): 
        super().__init__()
        self.model_name = model

    def chat(self, messages,stream=False): 
        response = ollama.chat(model=self.model_name, messages=messages,stream=stream) 
        if stream:
            for chunks in response:
                yield chunks 
        else:
            return response[ 'message' ][ 'content' ] 

    def stream(self, query): 
        text = query
        for chunks in ollama.generate(model=self.model_name, prompt=query, stream=True): 
            self.trigger(self.STREAMING_TOKEN_EVENT,chunks)
            text += chunks['response']
            yield chunks 
        self.trigger(self.STREAMING_FINISHED_EVENT)
