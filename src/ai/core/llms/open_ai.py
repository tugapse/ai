import os
import threading
import gc
from .base_llm import BaseModel
import functions as func


class OpenAIAPIModel(BaseModel):
    """
    Lazy-loading OpenAI implementation of BaseModel.
    Supports streaming and text completion (Vision can be extended).
    """
    def __init__(self, model_name="gpt-4o", system_prompt=None, api_key=None, **kargs):
        super().__init__(model_name, system_prompt, **kargs)
        
        # --- LAZY IMPORT ---
        try:
            from openai import OpenAI
            self.openai_class = OpenAI
        except ImportError:
            func.log("ERROR: 'openai' package not found.")
            func.log("Please run: pip install openai")
            raise ImportError("Missing 'openai' dependency.")

        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API Key is required.")
            
        self.client = self.openai_class(api_key=self.api_key)
        
        self.options = {
            "temperature": kargs.get('temperature', 0.5),
            "max_tokens": kargs.get('max_new_tokens', 2048),
            "top_p": kargs.get('top_p', 0.95),
            "presence_penalty": kargs.get('presence_penalty', 0.0),
            "frequency_penalty": kargs.get('frequency_penalty', 0.0),
        }

    def _convert_messages(self, messages: list):
        """Converts internal format to OpenAI format."""
        formatted = []
        if self.system_prompt:
            formatted.append({"role": "system", "content": self.system_prompt})
            
        for msg in messages:
            if msg['role'] == 'system': continue
            formatted.append({"role": msg['role'], "content": msg['content']})
        return formatted

    def chat(self, messages: list, images: list = None, stream: bool = True, options: object = None):
        self.stop_generation_event.clear()
        formatted_msgs = self._convert_messages(messages)

        try:
            if stream:
                self._generation_thread = threading.Thread(
                    target=self._run_streaming_chat, 
                    args=(formatted_msgs,)
                )
                self._generation_thread.start()
            else:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=formatted_msgs,
                    stream=False,
                    **self.options
                )
                return response.choices[0].message.content
        except Exception as e:
            func.error(f"OpenAI Error: {e}")
            self.trigger(BaseModel.STREAMING_FINISHED_EVENT)

    def _run_streaming_chat(self, formatted_msgs):
        try:
            stream = self.client.chat.completions.create(
                model=self.model_name,
                messages=formatted_msgs,
                stream=True,
                **self.options
            )

            for chunk in stream:
                if self.stop_generation_event.is_set():
                    break
                if chunk.choices and chunk.choices[0].delta.content:
                    self.trigger("token", chunk.choices[0].delta.content)
        except Exception as e:
            func.error(f"OpenAI Stream Error: {e}")
        finally:
            self.trigger(BaseModel.STREAMING_FINISHED_EVENT)

    def clean_cache(self): gc.collect()