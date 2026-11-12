import sys
import threading
import queue
import gc
import ctypes
from typing import List, Dict, Any, NoReturn
from huggingface_hub import hf_hub_download
from llama_cpp import Llama, llama_log_set

import ai.functions as func
from ai.core.llms.base_llm import BaseModel, ModelParams
from ai.color import Color
from ai.tools.tool_registry import ToolRegistry

def _null_log_callback(level, message, user_data):
    """A null callback function to suppress logging from llama_cpp."""
    pass
_log_callback_type = ctypes.CFUNCTYPE(None, ctypes.c_int, ctypes.c_char_p, ctypes.c_void_p)
_callback_ref = _log_callback_type(_null_log_callback)
llama_log_set(_callback_ref, ctypes.c_void_p())

class GGUFImageLLM(BaseModel):
    """
    JARVIS GGUF Engine - Inference only. Protocol injection handled externally by Orchestrator.

    This class implements the LLM interface using the llama-cpp bindings for GGUF models.
    It handles model loading, tokenization, streaming inference, and resource management.
    """
    _shared_mem_lock = threading.Lock()
    def __init__(
        self,
        model_name: str,
        gguf_filename: str,
        model_repo_id: str = "",
        system_prompt: str = "",
        n_ctx: int = 4000,
        model_params: dict = {},
        **kwargs,
    ):
        """
        Initializes the GGUF LLM engine.

        Args:
            model_name: The display name for the model.
            gguf_filename: The specific filename of the GGUF model to load.
            model_repo_id: The Hugging Face repository ID where the model is hosted.
            system_prompt: The initial system prompt context for the model.
            n_ctx: The maximum context window size for the model.
            model_params: Dictionary of parameters to pass to Llama initialization (e.g., temperature).
            **kwargs: Additional keyword arguments passed to the base class.
        """
        super().__init__(model_name, system_prompt=system_prompt, **kwargs)
        func.log(f"Initializing GGUF: {model_name}")
        
        self.model_repo_id = model_repo_id
        self.gguf_filename = gguf_filename
        self._n_ctx = n_ctx
        self.llama_model = None
        self.error_queue = queue.Queue()
        self.token_info_count.max_context_window = self._n_ctx
        
        self.options = ModelParams(**model_params).to_dict() if model_params else {
            "max_new_tokens": 2048,
            "temperature": 0.7
        }

        func.debug(f"[GGUF Engine] Config loaded. Base max_new_tokens: {self.options.get('max_new_tokens')}, Context window (n_ctx): {self._n_ctx}")
    
        self._load_llm_params(**kwargs)

    def _load_llm_params(self, **kwargs) -> None:
        """
        Handles the process of downloading the GGUF file and initializing the Llama model object.

        Args:
            **kwargs: Additional keyword arguments passed during initialization.
        """
        super()._load_llm_params(**kwargs)
        kwargs.pop('verbose', None)
        kwargs.pop('print_timings', None)
        
        try:
            func.debug(f"[GGUF Engine] Checking local cache for model...")
            
            try:
                model_path = hf_hub_download(
                    repo_id=self.model_repo_id,
                    filename=self.gguf_filename,
                    local_files_only=True
                )
                func.log(f"Found model in local cache: {model_path}")
            except Exception:
                func.log(f"Model not found locally. Downloading {self.gguf_filename} from {self.model_repo_id}...")
                model_path = hf_hub_download(
                    repo_id=self.model_repo_id,
                    filename=self.gguf_filename,
                    local_files_only=False
                )
                func.log(f"Download complete: {model_path}")

            func.debug(f"[GGUF Engine] Loading model into memory...")
            
            with GGUFImageLLM._shared_mem_lock:
                self.llama_model = Llama(
                    model_path=model_path,
                    n_ctx=self._n_ctx,
                    verbose=False,
                    **kwargs
                )
            func.log(f"GGUF model '{self.model_name}' ready.")
            
        except Exception as e:
            func.error(f"Failed to load GGUF: {e}")
            # A half-built engine answers "Model not loaded." forever; let the caller decide.
            raise RuntimeError(f"Failed to load GGUF '{self.gguf_filename}': {e}") from e

    def _generate_in_thread(self, messages: List[Dict[str, str]], gen_options: dict, output_queue: queue.Queue):
        """
        The target function for the generation thread. Performs streaming inference using Llama.

        Args:
            messages: The conversation history to send to the model.
            gen_options: Dictionary containing generation parameters (e.g., max_new_tokens, temperature).
            output_queue: Queue used to stream results back to the main thread.
        """
        func.debug("[GGUF Engine] Stream thread started.")
        output_token_count = 0
        sentinel_buffer = ""
        is_intercepting = False
        
        try:
            self.token_info_count.max_output_tokens = gen_options.get("max_new_tokens", 1024)
            with GGUFImageLLM._shared_mem_lock:
                stream_iter = self.llama_model.create_chat_completion(
                    messages=messages,
                    stream=True,
                    max_tokens=gen_options.get("max_new_tokens", 1024),
                    temperature=gen_options.get("temperature", 0.7),
                    top_p=gen_options.get("top_p", 0.95),
                    stop=["System Response:", "User:"] 
                )

                full_response = ""
                for chunk in stream_iter:
                    if self.stop_generation_event.is_set(): break
                    delta = chunk["choices"][0]["delta"]
                    
                    # Handle Reasoning (Gemma/DeepSeek style)
                    reasoning = delta.get("reasoning_content", "")
                    if reasoning:
                        output_queue.put(f"{Color.ITALIC}{Color.NORMAL_BLACK}[Thinking: {reasoning}]{Color.RESET}")
                        continue

                    content = delta.get("content", "")
                    if content:
                        full_response += content
                        
                        # --- CLEAN SENTINEL CALL ---
                        out, sentinel_buffer, is_intercepting, should_stop = self.handle_sentinel(
                            content, is_intercepting, sentinel_buffer
                        )
                        
                        if out:
                            output_queue.put(out)
                            if not isinstance(out, dict): # Only count tokens for actual text
                                output_token_count += 1
                        
                        if should_stop:
                            func.debug("[SENTINEL] Tool detected. Terminating stream.")
                            break
                        # ----------------------------
                        
                self.token_info_count.printed_tokens_count = output_token_count
                
                # Final flush
                if is_intercepting and sentinel_buffer:
                    output_queue.put(sentinel_buffer)
            
            self._update_token_metrics(messages, gen_options)
            output_queue.put(None)
            self.trigger(BaseModel.STREAMING_FINISHED_EVENT, full_response)
            
        except Exception as e:
            func.error(f"[GGUF Engine] Error: {e}")
            output_queue.put(None)
        finally:
            self.stop_generation_event.clear()

    def _update_token_metrics(self, messages: List[Dict[str, str]], gen_options: dict):
        self.token_info_count.max_context_window = self._n_ctx
        self.token_info_count.max_output_tokens = gen_options.get("max_new_tokens", 1024)
        current_prompt_count = self.get_message_tokens(messages)
        self.token_info_count.prompt_count = current_prompt_count
        self.token_info_count.total_prompt_count = int(current_prompt_count) + int(self.token_info_count.printed_tokens_count)
        func.debug(f"[GGUF Engine] Metrics Updated: {self.token_info_count.get_log_string()}")

    def get_message_tokens(self, messages: List[Dict[str, str]]) -> int:
        try:
            full_content = ""
            for msg in messages:
                full_content += f"{msg['role']}\n{msg['content']}\n"
            
            with GGUFImageLLM._shared_mem_lock:
                tokens = self.llama_model.tokenize(full_content.encode('utf-8'))
            return len(tokens)
        except Exception as e:
            func.debug(f"[GGUF Engine] Tokenization failed: {e}")
            return sum(len(m['content']) for m in messages) // 4
    
    def chat(self, messages: list, images: list = None, stream: bool = True, options: dict = {}):
        """
        Returns a token generator when ``stream`` is True, otherwise the full response
        (text, or a parsed tool action). Not a generator itself, so the non-streaming
        result is returned directly instead of being hidden in StopIteration.
        """
        with GGUFImageLLM._shared_mem_lock:
            if not self.llama_model:
                func.error("[GGUF Engine] Attempted to chat but model is not loaded.")
                return iter(["Model not loaded."]) if stream else "Model not loaded."

        self.stop_generation_event.clear()

        # DEEP COPY: Protect history integrity
        safe_messages = [m.copy() for m in messages]

        if images:
            image_msg = self.load_images(images)
            if image_msg:
                for i in reversed(range(len(safe_messages))):
                    if safe_messages[i]["role"] == "user":
                        safe_messages[i]["content"] += f"\n{image_msg['content']}"
                        break

        # Refresh System Prompt context (Time, OS, etc.)
        safe_messages = self.check_system_prompt(safe_messages)
        self._update_token_metrics(safe_messages, options)

        current_options = self.options.copy()
        current_options.update(options)
        applied_max_new_tokens = current_options.get("max_new_tokens", 1024)

        raw_text_for_counting = "\n".join([str(m.get("content", "")) for m in safe_messages])
        try:
            with GGUFImageLLM._shared_mem_lock:
                est_prompt_tokens = len(self.llama_model.tokenize(raw_text_for_counting.encode("utf-8")))
        except Exception:
            est_prompt_tokens = "Unknown"

        func.debug(f"{Color.GREEN}[GGUF Engine] Starting chat | Max Tokens: {applied_max_new_tokens} | Est. Prompt Tokens: {est_prompt_tokens}")

        if stream:
            return self._stream_chat(safe_messages, current_options)
        return self._sync_chat(safe_messages, current_options, applied_max_new_tokens)

    def _stream_chat(self, safe_messages: list, current_options: dict):
        """Yields tokens (or a function_call dict) produced by the generation thread."""
        q = queue.Queue()
        self._generation_thread = threading.Thread(
            target=self._generate_in_thread,
            args=(safe_messages, current_options, q),
        )
        self._generation_thread.start()

        while True:
            try:
                token = q.get(timeout=0.1)
                if token is None: break

                if isinstance(token, dict) and token.get("type") == "function_call":
                    func.log(f"{Color.CYAN}[SENTINEL]: ACTION DETECTED -> {token['name']}{Color.RESET}")
                    self.trigger("tool_detected", token["name"])
                    yield token
                    return
                yield token
            except queue.Empty:
                # The thread always ends with a None sentinel; stop if it died without one.
                if self._generation_thread is None or not self._generation_thread.is_alive(): break
                continue

    def _sync_chat(self, safe_messages: list, current_options: dict, applied_max_new_tokens: int):
        """Runs a blocking completion and returns the text, or a parsed tool action."""
        func.debug("[GGUF Engine] Executing synchronous generation...")
        with GGUFImageLLM._shared_mem_lock:
            output = self.llama_model.create_chat_completion(
                messages=safe_messages,
                stream=False,
                max_tokens=applied_max_new_tokens,
                temperature=current_options.get("temperature", 0.7),
                top_p=current_options.get("top_p", 0.95)
            )

        text = output["choices"][0]["message"]["content"]
        usage = output.get("usage", {})
        p_tokens = usage.get("prompt_tokens", "Unknown")
        c_tokens = usage.get("completion_tokens", "Unknown")

        func.debug(f"{Color.GREEN}[GGUF Engine] Sync Complete. Prompt: {p_tokens} | Output: {c_tokens}")

        action = ToolRegistry.parse_manual_tags(text)
        self.trigger(BaseModel.STREAMING_FINISHED_EVENT, text)
        return action if action else text

    def list(self) -> list:
        if self.llama_model:
            return [{"name": self.model_name, "type": "GGUF_STABLE"}]
        return []

    def request_shutdown(self):
        func.debug("[GGUF Engine] Full shutdown requested. Unloading model.")
        super().request_shutdown()
        self.unload()

    def unload(self):
        """
        Frees the llama.cpp model. Safe to call more than once and from __del__.

        Stops a running generation first (it checks stop_generation_event per chunk), then drops
        the Llama object under the shared lock, closes it and clears the CUDA cache.
        """
        if getattr(self, "llama_model", None) is None:
            func.debug("[GGUF Engine] Unload called but model is already None.")
            return

        func.log(f"BrainHub: Unloading {self.model_name}...")
        self.stop_generation_event.set()

        thread = getattr(self, "_generation_thread", None)
        if thread is not None and thread.is_alive() and thread is not threading.current_thread():
            func.debug("[GGUF Engine] Waiting for generation thread to finish...")
            thread.join(timeout=5.0)
            if thread.is_alive():
                func.error("[GGUF Engine] Generation thread did not terminate in time.")

        with GGUFImageLLM._shared_mem_lock:
            model_to_unload = self.llama_model
            self.llama_model = None
            self._generation_thread = None

        if model_to_unload is not None:
            func.debug("[GGUF Engine] Closing Llama model...")
            try:
                model_to_unload.close()
            except Exception as e:
                func.debug(f"[GGUF Engine] Llama.close() failed: {e}")
            del model_to_unload
            gc.collect()
            try:
                import torch
                if torch.cuda.is_available():
                    func.debug("[GGUF Engine] Clearing CUDA cache...")
                    torch.cuda.empty_cache()
            except ImportError:
                func.debug("[GGUF Engine] PyTorch not found, skipping CUDA cache clear.")
            except Exception as e:
                func.error(f"[GGUF Engine] Error clearing CUDA cache: {e}")

        self.stop_generation_event.clear()
        func.log(f"BrainHub: Resources cleared for {self.model_name}.")

    def __del__(self):
        # During interpreter shutdown llama_cpp may already be torn down; freeing then can crash.
        if sys.is_finalizing():
            return
        try:
            self.unload()
        except Exception:
            pass
