import ollama

import tools
from color import Color, format_text, pformat_text
from chat import ChatRoles
from events import Events


class LLMBot(Events):

    STREAMING_FINISHED_EVENT = "streaming_finished"
    STREAMING_TOKEN_EVENT = "streaming_token"


    def __init__(self, model,system_prompt=None): 
        super().__init__()
        self.model_name = model
        self.system_prompt = system_prompt

        #Ollama Options Documentation
        # -> https://github.com/ollama/ollama/blob/main/docs/modelfile.md#parameter
        self.llm_options_params_type = {
            'mirostat': 'int',
            'mirostat_eta': float,
            'mirostat_tau': float,
            'num_ctx': int,
            'repeat_last_n': int,
            'repeat_penalty': float,
            'temperature': float,
            'seed': int,
            'stop': str,
            'tfs_z': float,
            'num_predict': int,
            'top_k': int,
            'top_p': float

        }
        self.llm_options = {
            'num_ctx': 16384,  # Default: 2048
        }

    def chat(self, messages:list, stream:bool=True, options:object = {}):
        new_messages = self.check_system_prompt(messages)

        request_options = self.llm_options.copy()
        request_options.update(options)
        request_options_cleaner = []

        #Validate Used Options
        for key, value in request_options.items():
            if key not in self.llm_options_params_type:
                request_options_cleaner.append(key)
                print(f"{Color.YELLOW}# LLM Chat Option '{ key }' is an invalid option so it has been removed from request options")
            elif not isinstance(value, self.llm_options_params_type[key]):
                request_options_cleaner.append(key)
                print(f"{Color.YELLOW}# LLM Chat Option '{key}' should be of type ({self.llm_options_params_type[key].__name__}) and type ({type(value).__name__}) was given so it has been removed from request options")

        for key in request_options_cleaner:
            del request_options[key]

        response = ollama.chat(model=self.model_name, messages=new_messages,stream=stream, options= request_options)

        if stream:
            for chunks in response:
                yield chunks[ 'message' ][ 'content' ]
            self.trigger(self.STREAMING_FINISHED_EVENT)

        else:
            self.trigger(self.STREAMING_FINISHED_EVENT)
            yield response

        exit(0)
    def check_system_prompt(self,messages:list):
        if ChatRoles.SYSTEM not in [obj['role'] for obj in messages]:
            messages.insert(0,{'role':ChatRoles.SYSTEM,'content':self.system_prompt})
        return messages
    
    def create_message(self, role:ChatRoles, message:str):
        return {'role':role,'content':message}

    
