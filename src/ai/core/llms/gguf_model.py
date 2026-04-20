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
def _null_log_callback(level, message, user_data):
    pass
_log_callback_type = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_char_p, ctypes.c_void_p)
_callback_ref = _log_callback_type(_null_log_callback)
llama_log_set(_callback_ref, ctypes.c_void_p())

class GGUFImageLLM(BaseModel):
    """
    JARVIS GGUF Engine - Hardened for CPU.
    """
    _shared_mem_lock = threading.Lock()
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
        super().__init__(model_name, system_prompt=system_prompt,**kwargs)
        functions.log(f"Initializing Hardened GGUF: {model_name}")
        
        self.model_repo_id = model_repo_id
        self.gguf_filename = gguf_filename
        self._n_ctx = n_ctx
        self.llama_model = None
        self.error_queue = queue.Queue()
        self.token_info_count.max_context_window = self._n_ctx
        
        # Load config options
        self.options = ModelParams(**model_params).to_dict() if model_params else {
            "max_new_tokens":2048,
            "temperature": 0.7
        }

        functions.debug(f"[GGUF Engine] Config loaded. Base max_new_tokens: {self.options.get('max_new_tokens')}, Context window (n_ctx): {self._n_ctx}")
    
        self._load_llm_params(**kwargs)

    def _load_llm_params(self, **kwargs):
        kwargs.pop('verbose', None)
        kwargs.pop('print_timings', None)
        
        try:
            functions.debug(f"[GGUF Engine] Checking local cache for model...")
            
            try:
                model_path = hf_hub_download(
                    repo_id=self.model_repo_id,
                    filename=self.gguf_filename,
                    local_files_only=True
                )
                functions.log(f"Found model in local cache: {model_path}")
            except Exception:
                functions.log(f"Model not found locally. Downloading {self.gguf_filename} from {self.model_repo_id}...")
                model_path = hf_hub_download(
                    repo_id=self.model_repo_id,
                    filename=self.gguf_filename,
                    local_files_only=False
                )
                functions.log(f"Download complete: {model_path}")

            functions.debug(f"[GGUF Engine] Loading model into memory...")
            
            # Use lock during model initialization
            with GGUFImageLLM._shared_mem_lock:
                self.llama_model = Llama(
                    model_path=model_path,
                    n_ctx=self._n_ctx,
                    verbose=False,
                    **kwargs
                )
            functions.log(f"GGUF model '{self.model_name}' ready.")
            
        except Exception as e:
            functions.error(f"Failed to load GGUF: {e}")

    def _generate_in_thread(self, messages: List[Dict[str, str]], gen_options: dict, output_queue: queue.Queue):
        """Threaded generation using internal Chat API."""
        functions.debug("[GGUF Engine] Stream thread started.")
        output_token_count = 0
        
        try:
            self.token_info_count.max_output_tokens = gen_options.get("max_new_tokens", 1024)
            
            # The lock must wrap the creation AND iteration of the stream
            with GGUFImageLLM._shared_mem_lock:
                stream_iter = self.llama_model.create_chat_completion(
                    messages=messages,
                    stream=True,
                    max_tokens=gen_options.get("max_new_tokens", 1024),
                    temperature=gen_options.get("temperature", 0.7),
                    top_p=gen_options.get("top_p", 0.95)
                )

                full_response = ""
                for chunk in stream_iter:
                    if self.stop_generation_event.is_set():
                        functions.debug("[GGUF Engine] Generation stopped by user/system event.")
                        break
                    delta = chunk["choices"][0]["delta"]
                    
                    reasoning = delta.get("reasoning_content", "")
                    if reasoning:
                        output_queue.put(f"{Color.ITALIC}{Color.NORMAL_BLACK}[Thinking: {reasoning}]{Color.RESET}")
                        continue

                    content = delta.get("content", "")
                    if content:
                        full_response += content
                        output_token_count += 1
                        output_queue.put(content)
                    self.token_info_count.printed_tokens_count = output_token_count
            
            self._update_token_metrics(messages, gen_options)
            output_queue.put(None)
            self.trigger(BaseModel.STREAMING_FINISHED_EVENT, full_response)

            functions.log(f"{Color.NORMAL_BLACK}{Color.BG_BRIGHT_WHITE}{self.token_info_count.get_log_string()}{Color.RESET}", level="INFO")
            functions.debug(f"[GGUF Engine] Stream finished normally. Total chunks/tokens: {output_token_count}")
            
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            functions.error(f"[GGUF Engine] Error in generation thread: {e}\n{error_traceback}")
            self.error_queue.put(str(e))
            output_queue.put(None)
        finally:
            self.stop_generation_event.clear() 

    def _update_token_metrics(self, messages: List[Dict[str, str]], gen_options: dict):
        self.token_info_count.max_context_window = self._n_ctx
        self.token_info_count.max_output_tokens = gen_options.get("max_new_tokens", 1024)
        current_prompt_count = self.get_message_tokens(messages)
        self.token_info_count.prompt_count = current_prompt_count
        self.token_info_count.total_prompt_count = int(current_prompt_count) + int(self.token_info_count.printed_tokens_count)
        functions.debug(f"[GGUF Engine] Metrics Updated: {self.token_info_count.get_log_string()}")

    def get_message_tokens(self, messages: List[Dict[str, str]]) -> int:
        try:
            full_content = ""
            for msg in messages:
                full_content += f"{msg['role']}\n{msg['content']}\n"
            
            with GGUFImageLLM._shared_mem_lock:
                tokens = self.llama_model.tokenize(full_content.encode('utf-8'))
            return len(tokens)
        except Exception as e:
            functions.debug(f"[GGUF Engine] Tokenization failed: {e}")
            return sum(len(m['content']) for m in messages) // 4
    
    def chat(self, messages: list, images: list = None, stream: bool = True, options: dict = {}):
        # Initial check using lock
        with GGUFImageLLM._shared_mem_lock:
            if not self.llama_model:
                functions.error("[GGUF Engine] Attempted to chat but model is not loaded.")
                if stream: yield "Model not loaded."
                return "Model not loaded."

        self.stop_generation_event.clear()

        if images:
            image_msg = self.load_images(images)
            if image_msg:
                for i in reversed(range(len(messages))):
                    if messages[i]["role"] == "user":
                        messages[i]["content"] += f"\n{image_msg['content']}"
                        break

        messages = self.check_system_prompt(messages)
        self._update_token_metrics(messages, options)

        current_options = self.options.copy()
        current_options.update(options)
        applied_max_new_tokens = current_options.get("max_new_tokens", 1024)

        raw_text_for_counting = "\n".join([str(m.get("content", "")) for m in messages])
        try:
            with GGUFImageLLM._shared_mem_lock:
                est_prompt_tokens = len(self.llama_model.tokenize(raw_text_for_counting.encode("utf-8")))
        except Exception:
            est_prompt_tokens = "Unknown"

        functions.debug(f"{Color.GREEN}[GGUF Engine] Starting chat | Max Tokens: {applied_max_new_tokens} | Est. Prompt Tokens: {est_prompt_tokens}")

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
            functions.debug("[GGUF Engine] Executing synchronous generation...")
            with GGUFImageLLM._shared_mem_lock:
                output = self.llama_model.create_chat_completion(
                    messages=messages,
                    stream=False,
                    max_tokens=applied_max_new_tokens,
                    temperature=current_options.get("temperature", 0.7),
                    top_p=current_options.get("top_p", 0.95)
                )
            
            text = output["choices"][0]["message"]["content"]
            usage = output.get("usage", {})
            p_tokens = usage.get("prompt_tokens", "Unknown")
            c_tokens = usage.get("completion_tokens", "Unknown")
            
            functions.debug(f"{Color.GREEN}[GGUF Engine] Sync Complete. Prompt: {p_tokens} | Output: {c_tokens}")
            self.trigger(BaseModel.STREAMING_FINISHED_EVENT, text)
            return text

    def list(self) -> list:
        if self.llama_model:
            return [{"name": self.model_name, "type": "GGUF_STABLE"}]
        return []

    def unload(self):
        """
        Safely unloads the model by removing the reference, allowing Python's
        garbage collector to handle resource deallocation of the underlying C++ object.
        """
        if self.llama_model is None:
            functions.debug("[GGUF Engine] Unload called but model is already None.")
            return

        with GGUFImageLLM._shared_mem_lock:
            functions.log(f"BrainHub: Unloading {self.model_name}...")
            
            # 1. Signal any running generation threads to stop.
            self.stop_generation_event.set()
            if hasattr(self, '_generation_thread') and self._generation_thread.is_alive():
                functions.debug(f"[GGUF Engine] Waiting for generation thread to finish...")
                self._generation_thread.join(timeout=5.0) # Wait for thread to finish
                if self._generation_thread.is_alive():
                    functions.error("[GGUF Engine] Generation thread did not terminate in time.")

            # 2. Remove the model reference. Python's garbage collector will call the
            #    Llama object's __del__ method, which handles releasing the underlying
            #    C++ resources. This is the idiomatic and safe way to free memory.
            self.llama_model = None
            
            # 3. Explicitly trigger garbage collection. While often not necessary,
            #    for C++-backed objects, it can help ensure prompt cleanup.
            gc.collect()

            self.stop_generation_event.clear()
            functions.log(f"BrainHub: VRAM cleared for {self.model_name}.")

    def __del__(self):
        """
        Ensures resources are freed if the object is destroyed by the GC.
        """
        # Try to unload, but safely catch lock errors if Python is tearing down
        try:
            self.unload()
        except Exception:
            pass
  