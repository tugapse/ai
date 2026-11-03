import sys
import threading
import torch
from transformers import TextIteratorStreamer, StoppingCriteriaList
import ai.functions as func
from ai.core.llms.base_llm import BaseModel, ModelParams
from ai.core.events import Events
from ai.color import Color
from ai.tools.tool_registry import ToolRegistry

class CustomStoppingCriteria:
    """
    Custom stopping criteria used during model generation.

    This class checks a threading.Event to determine if generation should stop,
    allowing external control over the generation loop.
    """
    def __init__(self, stop_event: threading.Event):
        """
        Initializes the stopping criteria.

        Args:
            stop_event: The threading.Event object used to signal termination.
        """
        self.stop_event = stop_event

    def __call__(self, input_ids: 'torch.LongTensor', scores: 'torch.FloatTensor', **kwargs) -> bool:
        """
        Checks if the stop event is set.

        Args:
            input_ids: The input token IDs.
            scores: The scores tensor.
            **kwargs: Additional keyword arguments passed to the criteria.

        Returns:
            True if the stop event is set, indicating generation should stop.
        """
        return self.stop_event.is_set()

class HFEngineMixin:
    """
    Isolates the threading orchestration, inference parameters extraction, and chat iteration loops
    for Hugging Face model interactions.
    """

    def _extract_generation_params(self, options: dict) -> tuple:
        """
        Extracts and standardizes generation parameters from the provided options dictionary.

        It sets defaults for common generation parameters like max_new_tokens,
        do_sample, top_k, top_p, and temperature, and determines the appropriate
        EOS/PAD token ID.

        Args:
            options: A dictionary containing user-specified generation options.

        Returns:
            A tuple containing (max_new_tokens, do_sample, top_k, top_p, temperature, eos_token_id).
        """
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
            func.log("WARNING: No EOS or PAD token ID found for tokenizer. Model generation might not terminate cleanly.")
            eos_token_id = -1
            
        return max_new_tokens, do_sample, top_k, top_p, temperature, eos_token_id

    def _generate_in_thread(self, model, tokenizer, generation_kwargs, error_queue, streamer, stop_event: threading.Event):
        """
        Executes the model generation process in a separate thread.

        This method wraps model.generate() with error handling and integrates
        the CustomStoppingCriteria to allow external thread control.

        Args:
            model: The loaded Hugging Face model instance.
            tokenizer: The loaded Hugging Face tokenizer instance.
            generation_kwargs: Dictionary of arguments passed to model.generate.
            error_queue: A queue to place error messages if generation fails.
            streamer: The TextIteratorStreamer used for streaming output.
            stop_event: The threading.Event used to signal the thread to stop.
        """
        func.debug("_generate_in_thread started.")
        try:
            generation_kwargs["stopping_criteria"] = StoppingCriteriaList(
                [CustomStoppingCriteria(stop_event)]
            )
            func.debug(f"_generate_in_thread calling model.generate with kwargs keys: {generation_kwargs.keys()}")
            model.generate(**generation_kwargs)
            func.debug(f"_generate_in_thread model.generate completed (Streaming).")
        except RuntimeError as e:
            error_message = (
                f"ERROR: Model generation failed due to a CUDA/Runtime error. "
                f"\nDetails: {e}"
                f"\nSuggestion: Try reducing 'temperature', disable sampling (`do_sample=False`), or ensure bitsandbytes is correctly installed."
            )
            func.error(error_message)
            error_queue.put(error_message)
        except Exception as e:
            import traceback
            error_message = f"CRITICAL ERROR: An unexpected error occurred during model generation: {e}\nTraceback:\n{traceback.format_exc()}"
            func.error(error_message)
            error_queue.put(error_message)
        finally:
            func.debug("_generate_in_thread finally block executed. Clearing stop event. Calling streamer.end().")
            if streamer:
                streamer.end()
            stop_event.clear()

    def join_generation_thread(self, timeout: float = None):
        """
        Waits for the background generation thread to complete execution.

        If the thread is still running after the specified timeout, a warning is logged.

        Args:
            timeout: The maximum time in seconds to wait for the thread to join. Defaults to None (wait indefinitely).
        """
        if self._generation_thread and self._generation_thread.is_alive():
            func.log("Waiting for HuggingFace LLM generation thread to finish...")
            self._generation_thread.join(timeout=timeout)
            if self._generation_thread.is_alive():
                func.log("WARNING: HuggingFace LLM generation thread did not terminate within timeout.")
        self.stop_generation_event.clear()

    def _generate_response(self, input_data, options: dict = {}):
        """
        Synchronously generates a response from the loaded LLM using Hugging Face methods.

        This method prepares generation arguments, optionally injects TurboQuantCache
        for optimized inference, and calls model.generate().

        Args:
            input_data: The input data required for generation (e.g., tokenized input).
            options: A dictionary of optional generation parameters to override defaults.

        Returns:
            The decoded string response from the model.
        """
        if self.model is None or self.tokenizer is None:
            return "Model not loaded."

        max_tokens, sample, tk, tp, temp, eos_id = self._extract_generation_params(options)

        generation_kwargs = dict(
            **input_data,
            max_new_tokens=max_tokens,
            do_sample=sample,
            top_k=tk,
            top_p=tp,
            temperature=temp,
            pad_token_id=eos_id,
            eos_token_id=eos_id,
        )

        if self.turboquant_available:
            from turboquant import TurboQuantCache
            generation_kwargs["past_key_values"] = TurboQuantCache(bits=4)
            generation_kwargs["use_cache"] = True
            func.debug("TurboQuantCache injected into synchronous kwargs.")

        func.debug(f"_generate_response calling model.generate. max_new_tokens={max_tokens}, do_sample={sample}, temp={temp}, eos_token_id={eos_id}")
        outputs = self.model.generate(**generation_kwargs)
        func.debug(f"_generate_response model.generate completed. Outputs shape: {outputs.shape}")
        
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        escaped_response_chunk = response[:100].replace("\n", "\\n")
        func.debug(f"_generate_response decoded text length: {len(response)}. First 100 chars: '{escaped_response_chunk}'")
        return response

    def list(self):
        """
        Lists available Hugging Face models.

        Currently provides a static message indicating where to find models.

        Returns:
            A list containing a descriptive message.
        """
        func.log("Hugging Face models are available on huggingface.co/models. You can search there for available models.")
        return []

    def pull(self, model_name, stream=True):
        """
        Downloads and loads a specified Hugging Face model and tokenizer.

        Args:
            model_name: The identifier of the model to pull from Hugging Face.
            stream: If True, yields status messages during the pull process; otherwise, returns a single message.

        Yields:
            A status message if stream is True.

        Returns:
            A status message string if stream is False.
        """
        from transformers import AutoModelForCausalLM, AutoTokenizer
        func.log(f"Attempting to 'pull' (download/load) Hugging Face model: {model_name}")
        try:
            _ = AutoTokenizer.from_pretrained(model_name, local_files_only=False)
            _ = AutoModelForCausalLM.from_pretrained(model_name, local_files_only=False)
            message = f"Model {model_name} 'pulled' (downloaded/loaded) successfully."
            func.log(message)
            if stream:
                yield message
            else:
                return message
        except Exception as e:
            error_message_log = str(e).replace("\n", "\\n")
            message = f"Error 'pulling' model {model_name}: {error_message_log}"
            func.log(message)
            if stream:
                yield message
            else:
                return message