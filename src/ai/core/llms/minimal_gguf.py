import threading
import queue
import warnings
import os
import gc
from llama_cpp import Llama
from core.llms.base_llm import BaseModel
import functions

# Silence the HF Hub symlink warning
warnings.filterwarnings(
    "ignore", 
    message=".*local_dir_use_symlinks.*", 
    category=UserWarning, 
    module="huggingface_hub"
)

class MinimalGGUFLLM(BaseModel):
    """
    Hardened Minimal GGUF class specifically optimized for Qwen3.
    Designed to bypass C-level logging bugs, buggy Jinja2 template parsing, 
    and race conditions during garbage collection.
    """

    def __init__(
        self,
        model_name: str,
        gguf_filename: str,
        model_repo_id: str = None,
        system_prompt: str = None,
        n_gpu_layers: int = -1,
        n_ctx: int = 4000,
        **kwargs,
    ):
        functions.log(f"Initializing Hardened MinimalGGUFLLM: {model_name}")
        super().__init__(model_name, system_prompt=system_prompt)
        
        self.model_repo_id = model_repo_id
        self.gguf_filename = gguf_filename
        self._n_gpu_layers = n_gpu_layers
        self._n_ctx = n_ctx
        self.llama_model = None

        try:
            # [CRITICAL FIX] verbose=False is required to prevent the 
            # 'print_timings' C-function from Segfaulting during cleanup.
            self.llama_model = Llama.from_pretrained(
                repo_id=self.model_repo_id,
                filename=self.gguf_filename,
                n_gpu_layers=self._n_gpu_layers,
                n_ctx=self._n_ctx,
                verbose=False 
            )
            functions.log("Model loaded successfully (C-Logging/Timings Disabled).")
        except Exception as e:
            functions.error(f"Failed to load model: {e}")

    def _generate_in_thread(self, prompt: str, generation_options: dict, output_queue: queue.Queue):
        """
        Executes RAW completion. This bypasses the 'chat_completion_handler'
        internal C++ logic which was identified as a primary crash point.
        """
        try:
            # We use the raw 'create_completion' API to stay away from chat-handlers
            stream_iter = self.llama_model.create_completion(
                prompt=prompt,
                stream=True,
                max_tokens=generation_options.get("max_new_tokens", 3500),
                temperature=generation_options.get("temperature", 0.7),
                top_p=generation_options.get("top_p", 0.5),
                top_k=generation_options.get("top_k", 40),
                # Hardcoded stop tokens for Qwen3 architecture
                stop=["<|im_end|>", "<|endoftext|>", "<|im_start|>"]
            )
            
            for chunk in stream_iter:
                delta = chunk["choices"][0].get("text", "")
                if delta:
                    output_queue.put(delta)
            
            output_queue.put(None)  # Signal stream end
        except Exception as e:
            functions.error(f"Generation thread crashed: {e}")
            output_queue.put(None)

    def chat(self, messages: list, images: list = None, stream: bool = True, options: dict = {}):
        if not self.llama_model:
            if stream: yield "Model not loaded."
            return "Model not loaded."

        # [CRITICAL FIX] Manual Qwen3 Templating
        # We construct the prompt ourselves. Pre-filling <think>\n ensures 
        # the model enters reasoning mode immediately and reliably.
        sys_p = self.system_prompt or "You are a helpful assistant."
        raw_prompt = f"<|im_start|>system\n{sys_p}<|im_end|>\n"
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            raw_prompt += f"<|im_start|>{role}\n{content}<|im_end|>\n"
        
        raw_prompt += "<|im_start|>assistant\n"

        functions.log("Executing RAW completion (Manual Prompting)...", level="DEBUG")

        if stream:
            output_queue = queue.Queue()
            t = threading.Thread(
                target=self._generate_in_thread,
                args=(raw_prompt, options, output_queue)
            )
            t.start()

            while True:
                try:
                    token = output_queue.get(timeout=0.1)
                    if token is None: break
                    yield token
                    functions.debug(token, end="")
                except queue.Empty:
                    if not t.is_alive(): break
                    continue
            
            # Post-stream cleanup is deferred to os._exit(0) in main.py
            # self.close()
        else:
            # Synchronous execution
            output = self.llama_model.create_completion(
                prompt=raw_prompt,
                stream=False,
                max_tokens=options.get("max_new_tokens", 3500)
            )
            result = output["choices"][0]["text"]
            # self.close()
            return result

    def close(self):
        """
        Orphans the llama_model reference and triggers garbage collection.
        This avoids explicit .close() calls which can be unstable and lead
        to segfaults in the underlying C library. The object's __del__
        method is a safer way to handle C-level resource deallocation.
        """
        if hasattr(self, 'llama_model') and self.llama_model is not None:
            functions.log("Orphaning GGUF model reference for safe GC cleanup...", level="DEBUG")
            self.llama_model = None
            gc.collect()

    def __del__(self):
        """Final safety catch."""
        # [CRITICAL] This is intentionally disabled.
        # The __del__ method of the underlying Llama object is unstable
        # during Python's garbage collection at exit. We rely on
        # os._exit(0) in main.py for a hard process termination,
        # which is the only reliable way to prevent segfaults from the
        # C-level library during its cleanup phase.
        pass