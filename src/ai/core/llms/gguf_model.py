import os
import threading
import queue
import gc
from huggingface_hub import hf_hub_download
from llama_cpp import Llama

from huggingface_hub.errors import RepositoryNotFoundError, GatedRepoError
import requests.exceptions

from core.llms.base_llm import BaseModel, ModelParams
from core.events import Events
import functions
from color import Color
from typing import List, Dict, Any

# TEMPORARY HACK
import warnings

# This silences only the specific deprecation warning from huggingface_hub
warnings.filterwarnings(
    "ignore", 
    message=".*local_dir_use_symlinks.*", 
    category=UserWarning, 
    module="huggingface_hub"
)


class GGUFImageLLM(BaseModel):
    """
    A child class that extends BaseModel to use a GGUF model for text generation.
    This class integrates with llama-cpp-python to load and interact with GGUF models.
    It can process text descriptions related to images if provided in the prompt.
    """

    def __init__(
        self,
        model_name: str,
        gguf_filename: str,
        model_repo_id: str = None,
        system_prompt: str = None,
        n_gpu_layers: int = -1,
        n_ctx: int = None,
        verbose: bool = False,
        model_params=None,
        **kwargs,
    ):
        functions.log(f"Initializing GGUFImageLLM for model: {model_name}")
        super().__init__(model_name, system_prompt=system_prompt)
        self.gguf_filename = gguf_filename
        self.model_repo_id = model_repo_id
        self._n_gpu_layers = n_gpu_layers
        self._n_ctx = n_ctx
        self._verbose = verbose
        self.llama_model: Llama|None = None
        self._llama_init_kwargs = kwargs
        self.error_queue = queue.Queue()

        self.options = ModelParams(**model_params).to_dict()

        try:
            self._load_llm_params()
        except FileNotFoundError as e:
            functions.error(f"ERROR: Model '{self.gguf_filename}' not found. Details: {e}")
            self.llama_model = None
        except Exception as e:
            functions.error(f"ERROR: Failed to initialize Llama model for '{self.model_name}'. Details: {e}")
            self.llama_model = None
            import traceback
            functions.error(f"Traceback:\n{traceback.format_exc()}")

    def _load_llm_params(self):
        """Internal method to load the GGUF model from Hugging Face Hub or local path."""
        functions.log(f"Attempting to load GGUF model: {self.model_name}...")

        effective_n_ctx = (
            self._n_ctx
            if self._n_ctx is not None
            else self.options.get("num_ctx", BaseModel.CONTEXT_WINDOW_LARGE)
        )

        if self.model_repo_id and self.gguf_filename:
            try:
                self.llama_model = Llama.from_pretrained(
                    repo_id=self.model_repo_id,
                    filename=self.gguf_filename,
                    n_gpu_layers=self._n_gpu_layers,
                    n_ctx=effective_n_ctx,
                    verbose=self._verbose,
                    **self._llama_init_kwargs,
                )
                functions.log(f"GGUF model '{self.model_name}' loaded successfully via from_pretrained!")
                return
            except (
                RepositoryNotFoundError,
                GatedRepoError,
                requests.exceptions.RequestException,
            ) as e:
                functions.log(
                    f"WARNING: Llama.from_pretrained failed: {e}. Falling back to local check."
                )
            except Exception as e:
                functions.log(
                    f"WARNING: Llama.from_pretrained encountered unexpected error: {e}. Falling back to local check."
                )

        model_path = None
        if os.path.exists(self.gguf_filename):
            model_path = self.gguf_filename
            functions.log(f"Loading model from local path: {model_path}")
        elif self.model_repo_id and self.gguf_filename:
            try:
                model_path = hf_hub_download(
                    repo_id=self.model_repo_id, filename=self.gguf_filename
                )
                functions.log(f"Model downloaded to: {model_path}")
            except Exception as e:
                functions.error(f"ERROR: An unexpected error occurred during hf_hub_download: {e}.")

        if not model_path:
            raise FileNotFoundError(
                f"GGUF model '{self.gguf_filename}' not found locally or on Hub."
            )

        try:
            self.llama_model = Llama(
                model_path=model_path,
                n_gpu_layers=self._n_gpu_layers,
                n_ctx=effective_n_ctx,
                verbose=self._verbose,
                **self._llama_init_kwargs,
            )
            functions.log(f"GGUF model '{self.model_name}' loaded successfully!")
        except Exception as e:
            raise Exception(f"Failed to initialize llama_cpp model: {e}")

    def get_templated_prompt_tokens_info(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Robustly retrieves templated string and token info to match streaming logic.
        Handles cases where 'apply_chat_template' might be missing from the Llama object.
        """
        if not self.llama_model:
            functions.error("ERROR: Llama model not loaded. Cannot get token info.")
            raise RuntimeError("Llama model not loaded. Cannot get token info.")

        templated_string = ""

        # 1. Try modern API
        if hasattr(self.llama_model, "apply_chat_template"):
            try:
                templated_string = self.llama_model.apply_chat_template(
                    messages, add_generation_prompt=True
                )
                if isinstance(templated_string, bytes):
                    templated_string = templated_string.decode("utf-8")
            except Exception:
                pass

        # 2. Fallback to internal chat_handler (what create_chat_completion uses)
        if not templated_string:
            try:
                chat_handler = getattr(self.llama_model, "chat_handler", None)
                if chat_handler:
                    formatted = chat_handler(messages=messages)
                    templated_string = formatted.prompt
                else:
                    templated_string = self._format_messages_to_prompt(messages)
            except Exception:
                templated_string = self._format_messages_to_prompt(messages)

        # Tokenize
        encoded_str = templated_string.encode("utf-8")
        token_ids = self.llama_model.tokenize(encoded_str, add_bos=False)
        token_count = len(token_ids)

        token_strings = []
        for token_id in token_ids:
            try:
                token_str = self.llama_model.detokenize([token_id]).decode("utf-8", errors="replace")
                token_strings.append(token_str)
            except:
                token_strings.append(f"<ID_{token_id}>")

        return {
            "templated_string": templated_string,
            "token_ids": token_ids,
            "token_count": token_count,
            "token_strings": token_strings,
        }

    def _format_messages_to_prompt(self, messages: list) -> str:
        """Manual legacy formatter used as a fallback."""
        processed_messages = self.check_system_prompt(messages)
        formatted_prompt = ""
        for message in processed_messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            if role == "system":
                formatted_prompt += f"<<SYS>>\n{content}\n<</SYS>>\n\n"
            elif role == "user":
                formatted_prompt += f"[INST] {content} [/INST]"
            elif role == "assistant":
                formatted_prompt += f" {content} "
            formatted_prompt += "\n"
        return formatted_prompt.strip()

    def _generate_in_thread(self, messages: list, generation_options: dict, output_queue: queue.Queue):
        """Main generation thread with final token counting."""
        try:
            llama_params = {
                "max_tokens": generation_options.get("max_new_tokens", 200),
                "temperature": generation_options.get("temperature", 0.7),
                "top_k": generation_options.get("top_k", 50),
                "top_p": generation_options.get("top_p", 0.95),
                "presence_penalty": generation_options.get("presence_penalty", 0.0),
                "frequency_penalty": generation_options.get("frequency_penalty", 0.0),
            }

            stream_iter = self.llama_model.create_chat_completion(
                messages, stream=True, **llama_params
            )

            full_response_content = ""
            for chunk in stream_iter:
                if self.stop_generation_event.is_set():
                    break
                delta = chunk["choices"][0]["delta"].get("content", "")
                full_response_content += delta
                output_queue.put(delta)

            # LOG OUTPUT TOKEN COUNT
            output_tokens = self.llama_model.tokenize(full_response_content.encode("utf-8"), add_bos=False)
            functions.log(full_response_content)
            functions.log(f"{Color.GREEN}Streaming Finished. Output tokens: {len(output_tokens)}/{llama_params.get('max_tokens')}{Color.RESET}")

            output_queue.put(None)
            self.trigger(BaseModel.STREAMING_FINISHED_EVENT, full_response_content)
        except Exception as e:
            self.error_queue.put(str(e))
            output_queue.put(None)
        finally:
            self.stop_generation_event.clear()

    def join_generation_thread(self, timeout: float = None):
        super().join_generation_thread(timeout)
        if self.is_gpu_available():
            gc.collect()

    def chat(self, messages: list, images: list = None, stream: bool = True, options: object = {}):
        if self.llama_model is None:
            if stream: yield "Model not loaded."
            return "Model not loaded."

        self.stop_generation_event.clear()
        while not self.error_queue.empty():
            self.error_queue.get()

        if images:
            image_message = self.load_images(images)
            if image_message:
                for i in reversed(range(len(messages))):
                    if messages[i]["role"] == "user":
                        messages[i]["content"] += f"\n{image_message['content']}"
                        break
                else:
                    messages.append(image_message)

        current_options = self.options.copy()
        current_options.update(options)

        functions.log(f"Context token: {self.get_templated_prompt_tokens_info(messages).get('token_count')}/{self._n_ctx}" ,level="DEBUG")

        if stream:
            output_queue = queue.Queue()
            self._generation_thread = threading.Thread(
                target=self._generate_in_thread,
                args=(messages, current_options, output_queue),
            )
            self._generation_thread.start()

            while True:
                try:
                    token = output_queue.get(timeout=0.1)
                    if token is None: break
                    yield token
                except queue.Empty:
                    if not self._generation_thread.is_alive(): break
                    continue
        else:
            response_text = self._generate_response_sync(messages, current_options)
            yield response_text

    def _generate_response_sync(self, messages: list, options: dict = {}):
        """Unified sync generation with final token counting."""
        llama_params = {
            "max_tokens": options.get("max_new_tokens", 200),
            "temperature": options.get("temperature", 0.7),
        }
        output = self.llama_model.create_chat_completion(
            messages, stream=False, **llama_params
        )
        response_text = output["choices"][0]["message"]["content"]
        
        # LOG OUTPUT TOKEN COUNT
        output_tokens = self.llama_model.tokenize(response_text.encode("utf-8"), add_bos=False)
        functions.log(f"{Color.GREEN}Sync Generation Finished. Output tokens: {len(output_tokens)}{Color.RESET}",level="DEBUG")

        self.trigger(BaseModel.STREAMING_FINISHED_EVENT, response_text)
        return response_text

    def list(self) -> list:
        if self.llama_model:
            return [{
                "name": self.model_name,
                "gguf_filename": self.gguf_filename,
                "n_ctx": self.llama_model.n_ctx(),
                "type": "GGUF",
            }]
        return []

    def pull(self, model_name_or_repo_id: str, gguf_filename: str = None, stream: bool = True):
        try:
            downloaded_path = hf_hub_download(repo_id=model_name_or_repo_id, filename=gguf_filename)
            return downloaded_path
        except Exception as e:
            return str(e)