import ollama
from tqdm import tqdm
import sys
import threading

from core.events import Events
from .base_llm import BaseModel, ModelParams
import functions


class OllamaModel(BaseModel):
    """
    This class implements an LLM bot using the Ollama library.
    """

    def __init__(self, model_name, system_prompt=None, host=None, keep_alive=False,model_params=None,**kargs):
        super().__init__(model_name, system_prompt)
        self.server_ip = host or "127.0.0.1"
        self.model = ollama.Client(self.server_ip)
        self.pull(self.model_name)
        self.keep_alive = keep_alive
        self.options = model_params or ModelParams().to_dict()

    def join_generation_thread(self, timeout: float = None):
        """
        Placeholder for joining the generation thread for OllamaModel.
        As Ollama's streaming is synchronous, there's no separate thread to join for generation.
        We just clear the stop event.
        """
        functions.out("INFO: OllamaModel does not use a separate generation thread for generation. Clearing stop event.")
        self.stop_generation_event.clear()


    def chat(self, messages: list, images:list[str] = None, stream: bool = True, options: object = {}):
        """
        Allows the bot to chat with users.
        """
        gen_options = self.options.copy()
        gen_options.update(options)

        new_messages = self.check_system_prompt(messages)
        
        if images is not None and len(images) > 0: new_messages.append(super().load_images(images))

        self.stop_generation_event.clear()

        if stream:
            try:
                response = self.model.chat(model=self.model_name, messages=new_messages,
                                           stream=stream, options=self.options, keep_alive=self.keep_alive)
                for chunks in response:
                    yield chunks['message']['content']
                    if self.stop_generation_event.is_set():
                        functions.log("INFO: Ollama generation interrupted by stop event.")
                        response.close()
                        break
            except KeyboardInterrupt:
                functions.log("\nINFO: Ctrl+C detected. Stopping Ollama generation...")
                if 'response' in locals() and hasattr(response, 'close'):
                    try:
                        response.close()
                    except Exception as e:
                        functions.log(f"WARNING: Error closing Ollama stream: {e}")
            except Exception as e:
                functions.log(f"\nCRITICAL ERROR: An unexpected error occurred during Ollama generation: {e}")
                import traceback
                traceback.functions.out_exc()
                sys.exit(1)

        else:
            try:
                response = self.model.chat(model=self.model_name, messages=new_messages,
                                           stream=False, options=gen_options)
                return response['message']['content']
            except Exception as e:
                functions.log(f"\nCRITICAL ERROR: An unexpected error occurred during Ollama (non-streaming) generation: {e}")
                import traceback
                traceback.functions.out_exc()
                sys.exit(1)


    def list(self):
        return self.model.list()

    def pull(self, model_name, stream=True):
        if not ":" in model_name:   model_name += ":latest"
        
        models = self.model.list().get("models")
        for model in models:
            if model.get("model") == model_name: return 
        self.__pull_model(model_name, self.model)

    def __pull_model(self,model_name,ollama_inst):
        current_digest, bars = '', {}                                                                                                                                               
                                                                                                                                                                                    
        for progress in ollama_inst.pull(model_name, stream=True):                                                                                                                       
            digest = progress.get('digest', '')                                                                                                                                     
                                                                                                                                                                                    
            if digest != current_digest and current_digest in bars:                                                                                                                 
                bars[current_digest].close()                                                                                                                                        
                                                                                                                                                                                    
            if not digest:                                                                                                                                                          
                functions.log(progress.get('status'))
                continue                                                                                                                                                            
                                                                                                                                                                                    
            if digest not in bars and (total := progress.get('total')):                                                                                                               
                bars[digest] = tqdm(total=total, desc=f'pulling {digest[7:19]}', unit='B', unit_scale=True)                                                                         
                                                                                                                                                                                    
            if completed := progress.get('completed'):                                                                                                                              
                bars[digest].update(completed - bars[digest].n)                                                                                                                 
                                                                                                                                                                                    
            current_digest = digest
