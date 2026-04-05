import os
import threading
import queue
import gc
import ctypes
from typing import List, Dict, Any
from huggingface_hub import hf_hub_download
from llama_cpp import Llama, llama_log_set

from core.llms.base_llm import BaseModel, ModelParams
import functions
from color import Color

# --- GLOBAL STABILITY MUZZLE ---
# This kills C-level logs globally. It is your primary defense against
# the 'print_timings' crash identified in your logs.
def _null_log_callback(level, message, user_data):
    pass
_log_callback_type = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_char_p, ctypes.c_void_p)
_callback_ref = _log_callback_type(_null_log_callback)
llama_log_set(_callback_ref, ctypes.c_void_p())

class GGUFImageLLM(BaseModel):
    """
    JARVIS GGUF Engine - Hardened for CPU.
    This version survives system updates by aggressively silencing 
    C-level performance logging.
    """

    def __init__(
        self,
        model_name: str,
        gguf_filename: str,
        model_repo_id: str = None,
        system_prompt: str = None,
        n_ctx: int = 4000,
        model_params: dict = None,
        **kwargs,
    ):
        super().__init__(model_name, system_prompt=system_prompt)
        functions.log(f"Initializing Hardened GGUF: {model_name}")
        
        self.model_repo_id = model_repo_id
        self.gguf_filename = gguf_filename
        self._n_ctx = n_ctx
        self.llama_model = None
        self.error_queue = queue.Queue()
        
        # Load your config options
        self.options = ModelParams(**model_params).to_dict() if model_params else {
            "max_tokens": 1024,
            "temperature": 0.7
        }

        self._load_llm_params(**kwargs)

    def _load_llm_params(self, **kwargs):
        """
        Safety-first loader. We strip out the dangerous logging 
        parameters that cause the print_timings segfault.
        """
        # Safety net: pop these even if they are in your config file
        kwargs.pop('verbose', None)
        kwargs.pop('print_timings', None)
        
        try:
            self.llama_model = Llama.from_pretrained(
                repo_id=self.model_repo_id,
                filename=self.gguf_filename,
                n_ctx=self._n_ctx,
                verbose=False,
                **kwargs
            )
            functions.log(f"GGUF model '{self.model_name}' ready.")
        except Exception as e:
            functions.error(f"Failed to load GGUF: {e}")

    def _generate_in_thread(self, messages: List[Dict[str, str]], gen_options: dict, output_queue: queue.Queue):
        """Threaded generation using internal Chat API."""
        try:
            stream_iter = self.llama_model.create_chat_completion(
                messages=messages,
                stream=True,
                max_tokens=gen_options.get("max_tokens", 1024),
                temperature=gen_options.get("temperature", 0.7),
                top_p=gen_options.get("top_p", 0.95)
            )

            full_response = ""
            for chunk in stream_iter:
                if self.stop_generation_event.is_set():
                    break
                
                delta = chunk["choices"][0]["delta"].get("content", "")
                full_response += delta
                output_queue.put(delta)

            output_queue.put(None)
            self.trigger(BaseModel.STREAMING_FINISHED_EVENT, full_response)
            
        except Exception as e:
            self.error_queue.put(str(e))
            output_queue.put(None)
        finally:
            self.stop_generation_event.clear()

    def chat(self, messages: list, images: list = None, stream: bool = True, options: dict = {}):
        if not self.llama_model:
            if stream: yield "Model not loaded."
            return "Model not loaded."

        self.stop_generation_event.clear()

        # Your original image logic
        if images:
            image_msg = self.load_images(images)
            if image_msg:
                for i in reversed(range(len(messages))):
                    if messages[i]["role"] == "user":
                        messages[i]["content"] += f"\n{image_msg['content']}"
                        break

        # Check system prompt and merge call options
        messages = self.check_system_prompt(messages)
        current_options = self.options.copy()
        current_options.update(options)

        if stream:
            q = queue.Queue()
            self._generation_thread = threading.Thread(
                target=self._generate_in_thread,
                args=(messages, current_options, q),
            )
            self._generation_thread.start()

            while True:
                try:
                    token = q.get(timeout=0.1)
                    if token is None: break
                    yield token
                except queue.Empty:
                    if not self._generation_thread.is_alive(): break
                    continue
        else:
            # Sync mode
            output = self.llama_model.create_chat_completion(
                messages=messages,
                stream=False,
                max_tokens=current_options.get("max_tokens", 1024)
            )
            text = output["choices"][0]["message"]["content"]
            self.trigger(BaseModel.STREAMING_FINISHED_EVENT, text)
            return text

    def list(self) -> list:
        if self.llama_model:
            return [{"name": self.model_name, "type": "GGUF_STABLE"}]
        return []

    def __del__(self):
        pass