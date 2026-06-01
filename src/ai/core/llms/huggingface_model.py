import logging
import os
import threading
import sys
import queue
import gc
import warnings

os.environ['BITSANDBYTES_NOWELCOME'] = '1'
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
warnings.filterwarnings("ignore", category=FutureWarning, module="bitsandbytes")
os.environ["TRANSFORMERS_VERBOSITY"] = "error"

import torch
from transformers import TextIteratorStreamer
from huggingface_hub.errors import RepositoryNotFoundError, GatedRepoError
import requests.exceptions

import ai.functions as func
from ai.core.llms.base_llm import BaseModel, ModelParams
from ai.core.events import Events
from ai.color import Color
from tools.tool_registry import ToolRegistry

# Relative import of your extracted logic folder
from .hf import HFModelLoaderMixin, HFPipelineMixin, HFEngineMixin


class HuggingFaceModel(HFModelLoaderMixin, HFPipelineMixin, HFEngineMixin, BaseModel):
    """
    Integrates Hugging Face models as an LLM. Handles loading, quantization (AWQ & BNB), and streaming.
    Defaults to Google TurboQuant for KV Cache compression if the environment supports it.
    """

    def __init__(self, model_name: str, system_prompt="", quantization_bits: int = 0, use_turboquant: bool = True, model_params=None, **kargs):
        func.debug(f"HuggingFaceModel __init__ called for model: {model_name}")
        super().__init__(model_name, system_prompt, **kargs)

        self.tokenizer = None
        self.model = None
        self.quantization_bits = quantization_bits
        self.error_queue = queue.Queue()
        self.options = model_params or ModelParams().to_dict()
        self.tokenizer_override = kargs.get("tokenizer_kwargs",{})
        self.quantization_method = kargs.get("quantization_method","bitsandbytes")
        self.device_map = kargs.get("device_map", "auto")
        self.use_turboquant = use_turboquant
        self.turboquant_available = False
        
        if self.use_turboquant:
            try:
                import turboquant
                if torch.cuda.is_available():
                    self.turboquant_available = True
                    func.log("TurboQuant: Valid environment detected. 4-bit KV Cache enabled by default.")
                else:
                    func.log("TurboQuant: Library found, but no CUDA device detected. Defaulting to standard cache.")
            except ImportError:
                func.log("TurboQuant: Module not found. To enable, pip install turboquant. Defaulting to standard cache.")

        try:
            self._load_llm_params()
        except GatedRepoError as e:
            func.error(f"ERROR: Failed to load gated model '{self.model_name}'. Access denied or not authenticated. Details: {e}")
            self.model = None
            self.tokenizer = None
            sys.exit(1)
        except RepositoryNotFoundError:
            func.error(f"ERROR: Model '{self.model_name}' not found on Hugging Face Hub. Check spelling.")
            self.model = None
            self.tokenizer = None
            sys.exit(1)
        except requests.exceptions.HTTPError as e:
            func.error(f"ERROR: Could not download model files for '{self.model_name}'. Check network, disk space, or proxy settings. Details: {e}")
            self.model = None
            self.tokenizer = None
            sys.exit(1)
        except Exception as e:
            func.error(f"CRITICAL ERROR: Model initialization failed for {self.model_name}: {e}")
            import traceback
            traceback.print_exc()
            self.model = None
            self.tokenizer = None
            sys.exit(1)

    def chat(self, messages: list, images: list[str] = [], stream: bool = True, options: object = {}):
        func.debug(f"HuggingFaceModel chat() called. Stream: {stream}")

        if self.model is None or self.tokenizer is None:
            yield "Model loading failed during initialization. Check logs for details."
            return

        self.stop_generation_event.clear()
        
        while not self.error_queue.empty():
            self.error_queue.get()

        func.debug("Chat method initialized, queues cleared.")

        safe_messages = [m.copy() for m in messages]
        processed_messages = self.check_system_prompt(safe_messages)

        processed_messages_log = processed_messages[-1]["content"][:50].replace("\n", "\\n") if processed_messages else "[No messages to process]"
        func.debug(f"Processed messages. Input for LLM will be based on: '{processed_messages_log}'...")

        if self.is_gpu_available():
            func.debug("Clearing CUDA cache before generation...")
            torch.cuda.empty_cache()
            gc.collect()

        input_data = self._prepare_input(processed_messages)
        func.debug(f"Input data prepared. Input IDs shape: {input_data['input_ids'].shape}")

        if hasattr(self.model, 'device'):
            inputs_on_device = {k: v.to(self.model.device) if hasattr(v, 'to') else v for k, v in input_data.items()}
        elif self.is_gpu_available() and self.device_map == "cuda":
            inputs_on_device = {k: v.to("cuda") if hasattr(v, 'to') else v for k, v in input_data.items()}
        else:
            inputs_on_device = input_data

        max_tokens, sample, tk, tp, temp, eos_id = self._extract_generation_params(options)
            
        text = f"Generation options: max_new_tokens={max_tokens}, do_sample={sample}, top_k={tk}, top_p={tp}, temperature={temp}, eos_token_id={eos_id}"
        func.debug(Color.GREEN + text)

        streamer = None
        if stream:
            streamer = TextIteratorStreamer(self.tokenizer, skip_prompt=True, skip_special_tokens=True)

        generation_kwargs = dict(
            inputs_on_device,
            max_new_tokens=max_tokens,
            do_sample=sample,
            top_k=tk,
            top_p=tp,
            temperature=temp,
            pad_token_id=eos_id,
            eos_token_id=eos_id,
            streamer=streamer if stream else None,
        )

        if self.turboquant_available:
            from turboquant import TurboQuantCache
            generation_kwargs["past_key_values"] = TurboQuantCache(bits=4)
            generation_kwargs["use_cache"] = True
            func.debug("TurboQuantCache injected into generation kwargs (4-bit mode).")

        if stream:
            func.debug("Entering streaming (threaded) generation path with TextIteratorStreamer.")
            self._generation_thread = threading.Thread(
                target=self._generate_in_thread,
                kwargs={
                    "model": self.model,
                    "tokenizer": self.tokenizer,
                    "generation_kwargs": generation_kwargs,
                    "error_queue": self.error_queue,
                    "streamer": streamer,
                    "stop_event": self.stop_generation_event,
                },
            )
            self._generation_thread.start()
            
            full_content = ""
            sentinel_buffer = ""
            is_intercepting = False

            try:
                for new_token in streamer:
                    if self.stop_generation_event.is_set():
                        break

                    out, sentinel_buffer, is_intercepting, should_stop = self.handle_sentinel(
                        new_token, is_intercepting, sentinel_buffer
                    )

                    if out:
                        if isinstance(out, dict) and out.get("type") == "function_call":
                            func.log(f"{Color.CYAN}[SENTINEL]: HF ACTION DETECTED -> {out['name']}{Color.RESET}")
                            self.trigger("tool_detected", out["name"])
                            self.stop_generation_event.set()
                            yield out
                            return
                        else:
                            full_content += out
                            yield out

                    if should_stop:
                        self.stop_generation_event.set()
                        break

                if is_intercepting and sentinel_buffer:
                    full_content += sentinel_buffer
                    yield sentinel_buffer

                func.debug("Streamer finished yielding all tokens.")

            except KeyboardInterrupt:
                func.log("\nInterrupted by user. Signaling thread to stop...")
                self.stop_generation_event.set()
                yield "\n[Generation stopped by user]"
                return
            finally:
                if self._generation_thread and self._generation_thread.is_alive():
                    func.debug("Waiting for generation thread to join...")
                    self._generation_thread.join(timeout=5.0)
                    if self._generation_thread.is_alive():
                        func.log("Warning: Generation thread did not join cleanly.")
                self.trigger(BaseModel.STREAMING_FINISHED_EVENT, full_content)
                func.debug("Chat method streaming block finished.")

            if not self.error_queue.empty():
                error_message = self.error_queue.get()
                func.log(f"ERROR: Error received from generation thread after streaming: {error_message}")

        else:
            func.debug("Entering non-streaming (synchronous) generation path.")
            try:
                response_text = self._generate_response(inputs_on_device, options)
                func.debug(f"Synchronous generation complete. Output length: {len(response_text)}. Yielding...")

                action = ToolRegistry.parse_manual_tags(response_text)
                
                if isinstance(self, Events):
                    func.debug("Triggering STREAMING_FINISHED_EVENT (synchronous path).")

                yield action if action else response_text

            except RuntimeError as e:
                error_message = (
                    f"ERROR: Model generation failed due to a CUDA/Runtime error."
                    f"\nDetails: {e}"
                    f"\nSuggestion: Try reducing 'temperature', disable sampling (`do_sample=False`), or ensure bitsandbytes is correctly installed."
                )
                func.error(error_message)
                sys.exit(1)
            except Exception as e:
                func.error(f"CRITICAL ERROR: An unexpected error occurred during model generation: {e}")
                import traceback
                traceback.print_exc()
                sys.exit(1)