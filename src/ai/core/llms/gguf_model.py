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
        self.llama_model = None
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
                    f"WARNING: Llama.from_pretrained failed (likely download/access issue or not found): {e}. Falling back to local check."
                )
            except Exception as e:
                functions.log(
                    f"WARNING: Llama.from_pretrained encountered unexpected error: {e}. Falling back to local check."
                )
                import traceback
                functions.log(f"Traceback:\n{traceback.format_exc()}")

        model_path = None
        if os.path.exists(self.gguf_filename):
            model_path = self.gguf_filename
            functions.log(f"Loading model from local path: {model_path}")
        elif self.model_repo_id and self.gguf_filename:
            try:
                model_path = hf_hub_download(
                    repo_id=self.model_repo_id, filename=self.gguf_filename
                )
                functions.log(f"Model downloaded to: {model_path} via hf_hub_download.")
            except (
                RepositoryNotFoundError,
                GatedRepoError,
                requests.exceptions.RequestException,
            ) as e:
                functions.error(f"ERROR: Error downloading model from Hugging Face Hub with hf_hub_download: {e}.")
            except Exception as e:
                functions.error(f"ERROR: An unexpected error occurred during hf_hub_download: {e}.")
                import traceback
                functions.error(f"Traceback:\n{traceback.format_exc()}")

        if not model_path:
            raise FileNotFoundError(
                f"GGUF model '{self.gguf_filename}' not found locally and "
                f"could not be downloaded from '{self.model_repo_id}' (if provided)."
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
        Applies the model's chat template to the input messages and returns
        detailed tokenization information (templated string, token IDs,
        token count, and token string representations).

        Args:
            messages: A list of message dictionaries in OpenAI chat format, e.g.,
                      [{"role": "system", "content": "..."}]

        Returns:
            A dictionary containing:
            - 'templated_string': The string after applying the chat template.
            - 'token_ids': A list of integer token IDs.
            - 'token_count': The total number of tokens.
            - 'token_strings': A list of string representations for each token.
        """
        if not self.llama_model:
            functions.error("ERROR: Llama model not loaded. Cannot get token info.")
            raise RuntimeError("Llama model not loaded. Cannot get token info.")

        try:
            templated_string = self.llama_model.apply_chat_template(messages)
        except Exception as e:
            functions.error(f"ERROR: Failed to apply chat template for token info: {e}")
            import traceback
            functions.error(f"Traceback:\n{traceback.format_exc()}")
            raise ValueError(f"Failed to apply chat template: {e}. Ensure messages are correctly formatted.")

        encoded_templated_string = templated_string.encode("utf-8")
        token_ids = self.llama_model.tokenize(encoded_templated_string)
        token_count = len(token_ids)

        token_strings = []
        for token_id in token_ids:
            try:
                token_str = self.llama_model.detokenize([token_id]).decode("utf-8", errors="replace")
                token_strings.append(token_str)
            except Exception as e:
                functions.error(f"WARNING: Failed to detokenize token ID {token_id}: {e}")
                token_strings.append(f"<ERROR_DETOKENIZE_ID_{token_id}>")

        return {
            "templated_string": templated_string,
            "token_ids": token_ids,
            "token_count": token_count,
            "token_strings": token_strings,
        }

    def _format_messages_to_prompt(self, messages: list) -> str:
        """
        Formats a list of messages into a single string prompt.
        """
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

    def _generate_in_thread(
        self, messages: list, generation_options: dict, output_queue: queue.Queue
    ):
        """
        Target function for the generation thread.
        Handles model generation and puts tokens into the output_queue.
        Puts any caught exceptions into the error_queue.
        """
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
                    functions.log("INFO: Generation stopped by user request.")
                    break
                delta = chunk["choices"][0]["delta"].get("content", "")
                full_response_content += delta
                output_queue.put(delta)

            output_queue.put(None)
            self.trigger(BaseModel.STREAMING_FINISHED_EVENT, full_response_content)

        except Exception as e:
            import traceback
            error_message = f"CRITICAL ERROR: An unexpected error occurred during GGUF model generation: {e}"
            error_message += f"\nTraceback:\n{traceback.format_exc()}"
            functions.error(error_message)
            self.error_queue.put(error_message)
            output_queue.put(None)
        finally:
            self.stop_generation_event.clear()

    def join_generation_thread(self, timeout: float = None):
        """
        Waits for the background generation thread to complete.
        Overrides BaseModel's method.
        """
        super().join_generation_thread(timeout)
        if self.is_gpu_available():
            gc.collect()

    def chat(
        self,
        messages: list,
        images: list = None,
        stream: bool = True,
        options: object = {},
    ):
        """
        Generates a chat response from the GGUF model.
        When 'stream' is True, generation happens in a separate thread and yields tokens as they are generated.
        When 'stream' is False, generation happens in the main thread and yields the full response.
        """
        if self.llama_model is None:
            error_msg = (
                "GGUF model not loaded during initialization. Check logs for details."
            )
            functions.error(f"ERROR: {error_msg}")
            if stream:
                yield error_msg
            return error_msg

        self.stop_generation_event.clear()
        while not self.error_queue.empty():
            self.error_queue.get()

        if images:
            image_message = self.load_images(images)
            if image_message:
                last_user_message_index = -1
                for i in reversed(range(len(messages))):
                    if messages[i]["role"] == "user":
                        messages[i]["content"] += f"\n{image_message['content']}"
                        break
                else:
                    messages.append(image_message)

        # Note: processed_messages_for_logging is used only for non-streaming path
        # and for initial logging if `_format_messages_to_prompt` is relevant.
        processed_messages_for_logging = self._format_messages_to_prompt(messages)

        current_options = self.options.copy()
        current_options.update(options)

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
                    if token is None:
                        break
                    yield token
                except queue.Empty:
                    if (
                        not self._generation_thread.is_alive()
                        and self.error_queue.empty()
                    ):
                        break
                    if self.stop_generation_event.is_set():
                        break
                    continue

                if not self.error_queue.empty():
                    error_message = self.error_queue.get()
                    functions.error(
                        f"ERROR: Error received from generation thread during streaming: {error_message}"
                    )
                    yield f"\nERROR: {error_message}"
                    break

            if not self.error_queue.empty():
                error_message = self.error_queue.get()
                functions.error(
                    f"ERROR: Error received from generation thread after streaming: {error_message}"
                )
                yield f"\nERROR: {error_message}"

        else:
            try:
                response_text = self._generate_response_sync(
                    processed_messages_for_logging, current_options
                )
                self.trigger(BaseModel.STREAMING_FINISHED_EVENT, response_text)
                yield response_text
            except Exception as e:
                error_message = (
                    f"ERROR: GGUF model generation failed. "
                    f"This often indicates an issue with model execution or parameters."
                    f"\nDetails: {e}"
                )
                functions.error(error_message, level="ERROR")
                import traceback
                functions.error(f"Traceback:\n{traceback.format_exc()}")
                yield error_message

    def _generate_response_sync(self, prompt: str, options: dict = {}):
        """Generates a complete response without streaming (used by non-threaded path)."""
        if self.llama_model is None:
            return "GGUF model not loaded."

        llama_params = {
            "max_tokens": options.get("max_new_tokens", 200),
            "temperature": options.get("temperature", 0.7),
            "top_k": options.get("top_k", 50),
            "top_p": options.get("top_p", 0.95),
            "presence_penalty": options.get("presence_penalty", 0.0),
            "frequency_penalty": options.get("frequency_penalty", 0.0),
        }

        output = self.llama_model.create_completion(
            prompt, stream=False, **llama_params
        )

        response_text = output["choices"][0]["text"]
        return response_text

    def list(self) -> list:
        """
        Lists information about the currently loaded GGUF model.
        """
        functions.log(
            "GGUF models are typically loaded from local files or Hugging Face Hub. "
            "This list method shows info for the currently loaded model."
        )
        if self.llama_model:
            model_info = {
                "name": self.model_name,
                "gguf_filename": self.gguf_filename,
                "repo_id": self.model_repo_id,
                "n_ctx": self.llama_model.n_ctx(),
                "n_gpu_layers": self.llama_model.n_gpu_layers(),
                "type": "GGUF",
            }
            return [model_info]
        return []

    def pull(
        self, model_name_or_repo_id: str, gguf_filename: str = None, stream: bool = True
    ):
        """
        Pulls (downloads) a GGUF model from Hugging Face Hub.

        Args:
            model_name_or_repo_id (str): The Hugging Face Hub repository ID.
            gguf_filename (str, optional): The specific .gguf file name to download. Required if pulling.
            stream (bool): If True, yields status messages during download.
        """
        functions.log(
            f"Attempting to 'pull' (download) GGUF model: {model_name_or_repo_id} / {gguf_filename}"
        )

        if not gguf_filename:
            error_message = "ERROR: GGUF filename must be provided to pull a specific GGUF model."
            functions.error(error_message)
            if stream:
                yield error_message
            return error_message if not stream else None

        try:
            message_start = f"Downloading '{gguf_filename}' from '{model_name_or_repo_id}'..."
            functions.log(message_start)
            if stream:
                yield message_start

            downloaded_path = hf_hub_download(
                repo_id=model_name_or_repo_id, filename=gguf_filename
            )
            message_success = f"Model '{gguf_filename}' downloaded successfully to: {downloaded_path}"
            functions.log(message_success)
            if stream:
                yield message_success
            return downloaded_path

        except Exception as e:
            error_message = f"Error 'pulling' model {model_name_or_repo_id}/{gguf_filename}: {e}"
            functions.error(f"ERROR: {error_message}")
            if stream:
                yield error_message
            return error_message if not stream else None