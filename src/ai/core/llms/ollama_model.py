from typing import Optional

import ollama
from tqdm import tqdm

from ai.core.llms.api_retry import wrap_error
from ai.core.llms.base_llm import BaseModel, ModelParams
import ai.functions as func

PROVIDER = "Ollama"


class OllamaModel(BaseModel):
    """
    This class implements an LLM bot using the Ollama library.

    It handles initialization, model pulling, and conversational interaction
    with a local Ollama server instance.
    """

    def __init__(self, model_name, system_prompt="", host=None, keep_alive=False,model_params=None,**kargs):
        """
        Initializes the OllamaModel.

        Args:
            model_name (str): The name of the model to use (e.g., "llama2").
            system_prompt (str): The system prompt to guide the model's behavior.
            host (str, optional): The IP address of the Ollama server. Defaults to "127.0.0.1".
            keep_alive (bool, optional): Whether to keep the connection alive. Defaults to False.
            model_params (ModelParams, optional): Parameters to pass to the model. Defaults to None.
            **kargs: Additional keyword arguments passed to the base class constructor.
        """
        super().__init__(model_name, system_prompt,**kargs)
        self.server_ip = host or "127.0.0.1"
        self.model = ollama.Client(self.server_ip)
        self.pull(self.model_name)
        self.keep_alive = keep_alive
        self.options = model_params or ModelParams().to_dict()
        self._load_llm_params(**kargs)

    def join_generation_thread(self, timeout: float = 60.0):
        """
        Placeholder for joining the generation thread for OllamaModel.

        As Ollama's streaming is synchronous, there's no separate thread to join for generation.
        We just clear the stop event.

        Args:
            timeout (float, optional): The timeout duration for joining. Defaults to 60.0.
        """
        func.out("INFO: OllamaModel does not use a separate generation thread for generation. Clearing stop event.")
        self.stop_generation_event.clear()


    def chat(self, messages: list, images:list[str] = None, stream: bool = True, options: object = {}):
        """
        Allows the bot to chat with users.

        Args:
            messages (list): A list of message dictionaries for the conversation history.
            images (list[str], optional): A list of image paths to include in the prompt. Defaults to None.
            stream (bool, optional): If True, streams the response chunk by chunk. Defaults to True.
            options (object, optional): Additional generation options to override defaults. Defaults to {}.

        Yields:
            str: A chunk of the generated text content if streaming is enabled.
        Returns:
            str: The complete response content if streaming is disabled.

        Raises:
            KeyboardInterrupt: If the user interrupts the generation process (Ctrl+C).
            Exception: For critical errors during Ollama communication.
        """
        gen_options = self.options.copy()
        gen_options.update(options)

        new_messages = self.check_system_prompt(messages)
        
        if images is not None and len(images) > 0: new_messages.append(super().load_images(images))

        self.stop_generation_event.clear()

        if stream:
            return self._stream_chat(new_messages, gen_options)

        try:
            response = self.model.chat(model=self.model_name, messages=new_messages,
                                       stream=False, options=gen_options, keep_alive=self.keep_alive)
            return response['message']['content']
        except Exception as e:
            # Raised, not sys.exit: a server answers this request with an error and keeps serving;
            # the CLI reports LLMAPIError and keeps the chat alive.
            err = wrap_error(e, PROVIDER, attempts=1)
            func.error(f"[{PROVIDER}] {err.user_message()}")
            raise err from e

    def _stream_chat(self, new_messages: list, gen_options: Optional[dict] = None):
        """Yields response chunks. Kept apart so chat() is not a generator when stream=False."""
        produced = False
        try:
            response = self.model.chat(model=self.model_name, messages=new_messages, stream=True,
                                       options=gen_options if gen_options is not None else self.options,
                                       keep_alive=self.keep_alive)
            for chunks in response:
                produced = True
                yield chunks['message']['content']
                if self.stop_generation_event.is_set():
                    func.log("INFO: Ollama generation interrupted by stop event.")
                    response.close()
                    break
        except KeyboardInterrupt:
            func.error("\nINFO: Ctrl+C detected. Stopping Ollama generation...")
            if 'response' in locals() and hasattr(response, 'close'):
                try:
                    response.close()
                except Exception as e:
                    func.log(f"WARNING: Error closing Ollama stream: {e}")
        except Exception as e:
            err = wrap_error(e, PROVIDER, attempts=1, partial=produced)
            func.error(f"[{PROVIDER}] {err.user_message()}")
            raise err from e

    def list(self):
        """
        Retrieves a list of all available models on the Ollama server.

        Returns:
            dict: The response object containing the list of models from Ollama.
        """
        return self.model.list()

    def pull(self, model_name, stream=True):
        """
        Checks if a model exists locally and pulls it if it does not.

        Args:
            model_name (str): The name of the model to pull (e.g., "mistral").
            stream (bool, optional): Whether to stream the pull progress. Defaults to True.
        """
        if not ":" in model_name:   model_name += ":latest"
        
        models = self.model.list().get("models")
        for model in models:
            if model.get("model") == model_name: return 
        self.__pull_model(model_name, self.model)

    def __pull_model(self,model_name,ollama_inst):
        """
        Handles the actual process of pulling a model from the Ollama server,
        displaying progress using tqdm.

        Args:
            model_name (str): The name of the model to pull.
            ollama_inst (ollama.Client): The initialized Ollama client instance.
        """
        current_digest, bars = '', {}                                                                                                                                               
                                                                                                                                                                                    
        for progress in ollama_inst.pull(model_name, stream=True):                                                                                                                       
            digest = progress.get('digest', '')                                                                                                                                     
                                                                                                                                                                                    
            if digest != current_digest and current_digest in bars:                                                                                                                 
                bars[current_digest].close()                                                                                                                                        
                                                                                                                                                                                    
            if not digest:                                                                                                                                                          
                func.log(progress.get('status'))
                continue                                                                                                                                                            
                                                                                                                                                                                    
            if digest not in bars and (total := progress.get('total')):                                                                                                               
                bars[digest] = tqdm(total=total, desc=f'pulling {digest[7:19]}', unit='B', unit_scale=True)                                                                         
                                                                                                                                                                                    
            if completed := progress.get('completed'):                                                                                                                              
                bars[digest].update(completed - bars[digest].n)                                                                                                                 
                                                                                                                                                                                    
            current_digest = digest