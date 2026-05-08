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
from transformers import TextIteratorStreamer, StoppingCriteriaList
from huggingface_hub.errors import RepositoryNotFoundError, GatedRepoError
import requests.exceptions

from core.llms.base_llm import BaseModel, ModelParams
from core.events import Events
from color import Color
import functions


class CustomStoppingCriteria:
    """
    Custom StoppingCriteria to stop generation when a threading.Event is set.
    The `transformers.StoppingCriteria` parent class is added dynamically.
    """

    def __init__(self, stop_event: threading.Event):
        self.stop_event = stop_event

    def __call__(self, input_ids: 'torch.LongTensor', scores: 'torch.FloatTensor', **kwargs) -> bool:
        return self.stop_event.is_set()


class HuggingFaceModel(BaseModel):
    """
    Integrates Hugging Face models as an LLM. Handles loading, quantization (AWQ & BNB), and streaming.
    Defaults to Google TurboQuant for KV Cache compression if the environment supports it.
    """

    def __init__(self, model_name: str, system_prompt=None, quantization_bits: int = 0, use_turboquant: bool = True, model_params=None, **kargs):
        functions.debug(f"HuggingFaceModel __init__ called for model: {model_name}")
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
                    functions.log("TurboQuant: Valid environment detected. 4-bit KV Cache enabled by default.")
                else:
                    functions.log("TurboQuant: Library found, but no CUDA device detected. Defaulting to standard cache.")
            except ImportError:
                functions.log("TurboQuant: Module not found. To enable, pip install turboquant. Defaulting to standard cache.")

        try:
            self._load_llm_params()
        except GatedRepoError as e:
            functions.error(f"ERROR: Failed to load gated model '{self.model_name}'. Access denied or not authenticated. Details: {e}")
            self.model = None
            self.tokenizer = None
            sys.exit(1)
        except RepositoryNotFoundError:
            functions.error(f"ERROR: Model '{self.model_name}' not found on Hugging Face Hub. Check spelling.")
            self.model = None
            self.tokenizer = None
            sys.exit(1)
        except requests.exceptions.HTTPError as e:
            functions.error(f"ERROR: Could not download model files for '{self.model_name}'. Check network, disk space, or proxy settings. Details: {e}")
            self.model = None
            self.tokenizer = None
            sys.exit(1)
        except Exception as e:
            functions.error(f"CRITICAL ERROR: Model initialization failed for {self.model_name}: {e}")
            import traceback
            traceback.print_exc()
            self.model = None
            self.tokenizer = None
            sys.exit(1)

    def _load_llm_params(self):
        self.init_pytorch_cuda()
        import torch
        self.torch_lib = torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        functions.log(f"Preparing to load model: {self.model_name}...")

        load_kwargs = {"trust_remote_code": True}
        
        tokenizer_kwargs = {"trust_remote_code": True}
        overrides = self.options.get("tokenizer_kwargs", {})
        if overrides:
            tokenizer_kwargs.update(overrides)
            functions.debug(f"Applied tokenizer_kwargs from config: {overrides}")

        quant_method = self.quantization_method.lower()
        quantization_config = None

        if quant_method == "awq":
            functions.log("AWQ method selected from config. Expecting a pre-quantized AWQ model repository.")
        else:
            if self.quantization_bits in [4, 8]:
                try:
                    import bitsandbytes as bnb  
                    from transformers import BitsAndBytesConfig

                    # if hasattr(bnb.nn, 'Params4bit'):
                    #     original_new = bnb.nn.Params4bit.__new__
                    #     def patched_new(cls, *args, **kwargs):
                    #         kwargs.pop('_is_hf_initialized', None)
                    #         return original_new(cls, *args, **kwargs)
                    #     bnb.nn.Params4bit.__new__ = staticmethod(patched_new)

                    if self.quantization_bits == 4:
                        quantization_config = BitsAndBytesConfig(
                            load_in_4bit=True,
                            bnb_4bit_quant_type="nf4", 
                            bnb_4bit_compute_dtype=torch.bfloat16,
                            bnb_4bit_use_double_quant=True,
                            llm_int8_enable_fp32_cpu_offload=True
                        )
                        functions.log("Configured for 4-bit quantization using BitsAndBytesConfig.")
                    elif self.quantization_bits == 8:
                        quantization_config = BitsAndBytesConfig(
                            load_in_8bit=True, 
                            llm_int8_enable_fp32_cpu_offload=True
                        )
                        functions.log("Configured for 8-bit quantization using BitsAndBytesConfig.")

                except ImportError:
                    functions.log("WARNING: bitsandbytes not found. Falling back to non-quantized loading.")
                    self.quantization_bits = 0
                except Exception as e:
                    functions.log(f"ERROR: Could not create BitsAndBytesConfig for {self.quantization_bits}-bit quantization: {e}. Falling back to non-quantized loading.")
                    self.quantization_bits = 0

        if quantization_config:
            load_kwargs["quantization_config"] = quantization_config
            if self.is_gpu_available():
                load_kwargs["device_map"] = self.device_map
            functions.log(f"Attempting to load model: {self.model_name} with {self.quantization_bits}-bit BNB config.")
        else:
            if quant_method == "awq":
                functions.log("Loading AWQ model natively without BNB config.")
            else:
                functions.log("Loading model without quantization.")
            if self.is_gpu_available():
                load_kwargs["torch_dtype"] = torch.bfloat16
                load_kwargs["device_map"] = self.device_map

        try:
            functions.debug(f"Checking local cache for model {self.model_name}...")
            
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                local_files_only=True,
                **tokenizer_kwargs
            )
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            if self.is_gpu_available():
                torch.cuda.empty_cache()

            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                local_files_only=True,
                **load_kwargs

            )
            functions.log(f"Found model in local cache. Loaded: {self.model_name}")

        except Exception:
            functions.log(f"Model not found locally (or cache is incomplete). Downloading from HuggingFace...")
            
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                local_files_only=False,
                **tokenizer_kwargs
            )
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                local_files_only=False,
                **load_kwargs
            )
            functions.log(f"Successfully downloaded and loaded model: {self.model_name}")

    def _ensure_alternating_roles(self, messages: list) -> list:
        if not messages:
            return []

        cleaned_messages = []
        system_messages = [msg for msg in messages if msg["role"] == "system"]
        other_messages = [msg for msg in messages if msg["role"] != "system"]

        if system_messages:
            cleaned_messages.extend(system_messages)

        if not other_messages:
            return cleaned_messages

        current_message = {
            "role": other_messages[0]["role"],
            "content": other_messages[0]["content"],
        }

        for i in range(1, len(other_messages)):
            msg = other_messages[i]
            if msg["role"] == current_message["role"]:
                current_message["content"] += "\n" + msg["content"]
            else:
                cleaned_messages.append(current_message)
                current_message = {"role": msg["role"], "content": msg["content"]}

        cleaned_messages.append(current_message)

        if len(cleaned_messages) < len(messages):
            functions.log(f"WARNING: Chat history was cleaned to ensure alternating roles. Original length: {len(messages)}, Cleaned length: {len(cleaned_messages)}. Consider adjusting upstream history management.")

        return cleaned_messages

    def _generate_in_thread(self, model, tokenizer, generation_kwargs, error_queue, streamer, stop_event: threading.Event):
        functions.debug("_generate_in_thread started.")
        try:
            generation_kwargs["stopping_criteria"] = StoppingCriteriaList(
                [CustomStoppingCriteria(stop_event)]
            )

            functions.debug(f"_generate_in_thread calling model.generate with kwargs keys: {generation_kwargs.keys()}")
            model.generate(**generation_kwargs)
            functions.debug(f"_generate_in_thread model.generate completed (Streaming).")

        except RuntimeError as e:
            error_message = (
                f"ERROR: Model generation failed due to a CUDA/Runtime error. "
                f"\nDetails: {e}"
                f"\nSuggestion: Try reducing 'temperature', disable sampling (`do_sample=False`), or ensure bitsandbytes is correctly installed."
            )
            functions.error(error_message)
            error_queue.put(error_message)
        except Exception as e:
            import traceback
            error_message = f"CRITICAL ERROR: An unexpected error occurred during model generation: {e}\nTraceback:\n{traceback.format_exc()}"
            functions.error(error_message)
            error_queue.put(error_message)
        finally:
            functions.debug("_generate_in_thread finally block executed. Clearing stop event. Calling streamer.end().")
            if streamer:
                streamer.end()
            stop_event.clear()

    def join_generation_thread(self, timeout: float = None):
        if self._generation_thread and self._generation_thread.is_alive():
            functions.log("Waiting for HuggingFace LLM generation thread to finish...")
            self._generation_thread.join(timeout=timeout)
            if self._generation_thread.is_alive():
                functions.log("WARNING: HuggingFace LLM generation thread did not terminate within timeout.")
        self.stop_generation_event.clear()

    def chat(self, messages: list, images: list[str] = None, stream: bool = True, options: object = {}):
        functions.debug(f"HuggingFaceModel chat() called. Stream: {stream}")

        if self.model is None or self.tokenizer is None:
            yield "Model loading failed during initialization. Check logs for details."
            return

        self.stop_generation_event.clear()
        
        while not self.error_queue.empty():
            self.error_queue.get()

        functions.debug("Chat method initialized, queues cleared.")

        safe_messages = [m.copy() for m in messages]
        processed_messages = self.check_system_prompt(safe_messages)

        processed_messages_log = processed_messages[-1]["content"][:50].replace("\n", "\\n") if processed_messages else "[No messages to process]"
        functions.debug(f"Processed messages. Input for LLM will be based on: '{processed_messages_log}'...")

        if self.is_gpu_available():
            functions.debug("Clearing CUDA cache before generation...")
            torch.cuda.empty_cache()
            gc.collect()

        input_data = self._prepare_input(processed_messages)
        functions.debug(f"Input data prepared. Input IDs shape: {input_data['input_ids'].shape}")

        if self.is_gpu_available() and self.device_map == "cuda":
            inputs_on_device = {k: v.to("cuda") for k, v in input_data.items()}
        else:
            inputs_on_device = input_data

        gen_options = self.options.copy()
        gen_options.update(options)

        max_new_tokens = gen_options.get("max_new_tokens", 1024)
        do_sample = gen_options.get("do_sample", True)
        top_k = gen_options.get("top_k", 50)
        top_p = gen_options.get("top_p", 0.95)
        temperature = gen_options.get("temperature", 0.7)

        eos_token_id = self.tokenizer.eos_token_id
        if eos_token_id is None and hasattr(self.tokenizer, "pad_token_id"):
            eos_token_id = self.tokenizer.pad_token_id
        elif eos_token_id is None:
            functions.log("WARNING: No EOS or PAD token ID found for tokenizer. Model generation might not terminate cleanly.")
            eos_token_id = -1
            
        text = f"Generation options: max_new_tokens={max_new_tokens}, do_sample={do_sample}, top_k={top_k}, top_p={top_p}, temperature={temperature}, eos_token_id={eos_token_id}"
        functions.debug(Color.GREEN + text)

        streamer = None
        if stream:
            streamer = TextIteratorStreamer(self.tokenizer, skip_prompt=True, skip_special_tokens=True)

        generation_kwargs = dict(
            inputs_on_device,
            max_new_tokens=max_new_tokens,
            do_sample=do_sample,
            top_k=top_k,
            top_p=top_p,
            temperature=temperature,
            pad_token_id=eos_token_id,
            eos_token_id=eos_token_id,
            streamer=streamer if stream else None,
        )

        if self.turboquant_available:
            from turboquant import TurboQuantCache
            generation_kwargs["past_key_values"] = TurboQuantCache(bits=4)
            generation_kwargs["use_cache"] = True
            functions.debug("TurboQuantCache injected into generation kwargs (4-bit mode).")

        if stream:
            functions.debug("Entering streaming (threaded) generation path with TextIteratorStreamer.")
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
                            functions.log(f"{Color.CYAN}[SENTINEL]: HF ACTION DETECTED -> {out['name']}{Color.RESET}")
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

                functions.debug("Streamer finished yielding all tokens.")

            except KeyboardInterrupt:
                functions.log("\nInterrupted by user. Signaling thread to stop...")
                self.stop_generation_event.set()
                yield "\n[Generation stopped by user]"
                return
            finally:
                if self._generation_thread and self._generation_thread.is_alive():
                    functions.debug("Waiting for generation thread to join...")
                    self._generation_thread.join(timeout=5.0)
                    if self._generation_thread.is_alive():
                        functions.log("Warning: Generation thread did not join cleanly.")
                self.trigger(BaseModel.STREAMING_FINISHED_EVENT, full_content)
                functions.debug("Chat method streaming block finished.")

            if not self.error_queue.empty():
                error_message = self.error_queue.get()
                functions.log(f"ERROR: Error received from generation thread after streaming: {error_message}")

        else:
            functions.debug("Entering non-streaming (synchronous) generation path.")
            try:
                response_text = self._generate_response(inputs_on_device, gen_options)
                functions.debug(f"Synchronous generation complete. Output length: {len(response_text)}. Yielding...")

                action = self.parse_manual_tags(response_text)
                
                if isinstance(self, Events):
                    functions.debug("Triggering STREAMING_FINISHED_EVENT (synchronous path).")

                yield action if action else response_text

            except RuntimeError as e:
                error_message = (
                    f"ERROR: Model generation failed due to a CUDA/Runtime error."
                    f"\nDetails: {e}"
                    f"\nSuggestion: Try reducing 'temperature', disable sampling (`do_sample=False`), or ensure bitsandbytes is correctly installed."
                )
                functions.error(error_message)
                sys.exit(1)
            except Exception as e:
                functions.error(f"CRITICAL ERROR: An unexpected error occurred during model generation: {e}")
                import traceback
                traceback.print_exc()
                sys.exit(1)

    def _prepare_input(self, messages: list):
        if self.system_prompt and not any(m["role"] == "system" for m in messages):
            messages.insert(0, BaseModel.create_message("system", self.system_prompt))
            
        if hasattr(self.tokenizer, "apply_chat_template") and self.tokenizer.apply_chat_template is not None:
            input_string = self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            inputs = self.tokenizer(input_string, return_tensors="pt")
            functions.debug(f"_prepare_input using apply_chat_template. Input string length: {len(input_string)}")
            return inputs
        else:
            prepared_messages = []
            if self.system_prompt and not any(m["role"] == "system" for m in messages):
                prepared_messages.append(BaseModel.create_message("system", self.system_prompt))

            for msg in messages:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                prepared_messages.append(BaseModel.create_message(role, content))

            input_text = ""
            for msg in prepared_messages:
                if msg["role"] == "system":
                    input_text += f"System: {msg['content']}\n"
                elif msg["role"] == "user":
                    input_text += f"User: {msg['content']}\n"
                elif msg["role"] == "assistant":
                    input_text += f"Assistant: {msg['content']}\n"

            if messages and messages[-1]["role"] == "user":
                input_text += "Assistant:"

            inputs = self.tokenizer(input_text, return_tensors="pt")
            functions.debug(f"_prepare_input using manual formatting. Input text length: {len(input_text)}")
            return inputs

    def _generate_response(self, input_data, options: dict = {}):
        if self.model is None or self.tokenizer is None:
            return "Model not loaded."

        inputs = input_data

        max_new_tokens = options.get("max_new_tokens", 1024)
        do_sample = options.get("do_sample", True)
        top_k = options.get("top_k", 50)
        top_p = options.get("top_p", 0.95)
        temperature = options.get("temperature", 0.7)

        eos_token_id = self.tokenizer.eos_token_id
        if eos_token_id is None and hasattr(self.tokenizer, "pad_token_id"):
            eos_token_id = self.tokenizer.pad_token_id
        elif eos_token_id is None:
            functions.log("WARNING: No EOS or PAD token ID found for tokenizer. Model generation might not terminate cleanly.")
            eos_token_id = -1

        generation_kwargs = dict(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=do_sample,
            top_k=top_k,
            top_p=top_p,
            temperature=temperature,
            pad_token_id=eos_token_id,
            eos_token_id=eos_token_id,
        )

        if self.turboquant_available:
            from turboquant import TurboQuantCache
            generation_kwargs["past_key_values"] = TurboQuantCache(bits=4)
            generation_kwargs["use_cache"] = True
            functions.debug("TurboQuantCache injected into synchronous kwargs.")

        functions.debug(f"_generate_response calling model.generate. max_new_tokens={max_new_tokens}, do_sample={do_sample}, temp={temperature}, eos_token_id={eos_token_id}")

        outputs = self.model.generate(**generation_kwargs)
        functions.debug(f"_generate_response model.generate completed. Outputs shape: {outputs.shape}")
        
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        escaped_response_chunk = response[:100].replace("\n", "\\n")
        functions.debug(f"_generate_response decoded text length: {len(response)}. First 100 chars: '{escaped_response_chunk}'")

        return response

    def list(self):
        functions.log("Hugging Face models are available on huggingface.co/models. You can search there for available models.")
        return []

    def pull(self, model_name, stream=True):
        functions.log(f"Attempting to 'pull' (download/load) Hugging Face model: {model_name}")
        try:
            _ = AutoTokenizer.from_pretrained(model_name, local_files_only=False)
            _ = AutoModelForCausalLM.from_pretrained(model_name, local_files_only=False)
            message = f"Model {model_name} 'pulled' (downloaded/loaded) successfully."
            functions.log(message)
            if stream:
                yield message
            else:
                return message
        except Exception as e:
            error_message_log = str(e).replace("\n", "\\n")
            message = f"Error 'pulling' model {model_name}: {error_message_log}"
            functions.log(message)
            if stream:
                yield message
            else:
                return message