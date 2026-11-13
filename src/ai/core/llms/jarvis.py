import os
import gc
import json
from typing import Dict, List, Any, Optional, Union, Generator
import httpx

import ai.functions as func
from ai.core.llms.api_retry import LLMAPIError, RetryPolicy, call_with_retry, stream_with_retry, wrap_error
from ai.core.llms.base_llm import BaseModel

PROVIDER = "Jarvis"


class JarvisAiModel(BaseModel):
    """
    A drop-in client interface tailored for the JARVIS custom FastAPI endpoint.
    
    Maintains identical structure and event signaling to seamlessly interface 
    with the existing Orchestrator and Sentinel protocols.
    """

    def __init__(self, model_name: Optional[str] = None, system_prompt: str = "", api_key: Optional[str] = None, **kargs: Any):
        """
        Initializes the custom API endpoint model interface.

        Args:
            model_name: The name of the LLM model to use (defaults to "gpt-4o").
            system_prompt: The initial system prompt to guide the model's behavior.
            api_key: Optional API key for authentication (though not explicitly used in this interface).
            **kargs: Additional keyword arguments for configuration (the model JSON's model_properties):
                base_url (else AI_API_BASE_URL), server_model (the server's model config file name,
                else AI_SERVER_MODEL, else model_name), session_id, timeout, etc.
        """
        model_name = model_name or os.environ.get("AI_MODEL_NAME", "gpt-4o")
        super().__init__(model_name, system_prompt, **kargs)
        
        # Configuration routing pointing to the custom backend server
        self.base_url = kargs.get("base_url") or os.environ.get("AI_API_BASE_URL", "http://0.0.0.0:9999")
        self.endpoint = f"{self.base_url.rstrip('/')}/api/v1/chat/completions"
        # Which model config the server loads (its file name, e.g. "small"). model_name stays a display
        # name; it is only sent as the fallback for configs written before server_model existed.
        self.server_model = kargs.get("server_model") or os.environ.get("AI_SERVER_MODEL") or self.model_name
        
        # Session state details used by ChatSessionRouter on the backend
        self.session_id = kargs.get("session_id")
        self.session_folder = kargs.get("session_folder")
        
        func.log(f"JARVIS: Connecting to Custom Backend Interface [{self.model_name} -> server model '{self.server_model}'] -> {self.endpoint}")
        
        # Match standard token info context structural tracking
        out_tokens = kargs.get('max_new_tokens', 2048)
        self.token_info_count.max_output_tokens = out_tokens
        self.token_info_count.max_context_window = kargs.get("n_ctx", BaseModel.CONTEXT_WINDOW_128K)
        self.time_out = kargs.get("timeout", 600.0)  # Default to 10 minutes for long-running tasks
        # Connection drops, timeouts and 5xx are retried; then they surface as LLMAPIError,
        # never as an empty "model output" that the agent would treat as malformed.
        self.retry_policy = RetryPolicy.from_config({"timeout": self.time_out}, kargs, kargs.get("model_params") or {})

    def chat(self, messages: List[Dict[str, str]], images=[],stream: bool = True, options={} ) -> Union[str, Dict[str, Any], Generator[Union[str, Dict[str, Any]], None, None]]:
        """
        Executes a chat completion request directly to the custom backend endpoint.

        Args:
            messages: A list of message dictionaries containing conversation history.
            images: A list of image data (currently unused in payload construction).
            stream: If True, returns a generator for streaming responses; otherwise, returns the full response string.
            options: Additional options dictionary passed to the backend.

        Returns:
            Union[str, Dict[str, Any], Generator[Union[str, Dict[str, Any]], None, None]]: 
            The final text response, a dictionary response, or a generator yielding chunks.
        """
        self.stop_generation_event.clear()
        
        # Dynamic system prompt override sync matching original behavior
        injected_system_prompt = False
        for m in messages:
            if m.get('role') == 'system':
                self.system_prompt = m.get('content')
                injected_system_prompt = True
                break
        
        if not injected_system_prompt and self.system_prompt:
            messages.insert(0, {"role": "system", "content": self.system_prompt})

        # Construct payload targeting the backend ChatCompletionRequest schema
        payload = {
            "model": self.server_model,
            "system_prompt_content": self.system_prompt,
            "stream": stream,
            "session_id": self.session_id,
            "session_folder": self.session_folder,
            "messages": messages
        }

        if stream:
            return self._run_streaming_chat(payload)
        return self._run_sync_chat(payload)

    def _timeout(self) -> httpx.Timeout:
        return httpx.Timeout(self.retry_policy.timeout, connect=self.retry_policy.connect_timeout)

    def _run_sync_chat(self, payload: Dict[str, Any]) -> str:
        """
        Sends a non-streaming request and returns the full response text.

        Raises:
            LLMAPIError: If the server cannot be reached or answers with an error.
        """
        def request():
            with httpx.Client(timeout=self._timeout()) as client:
                response = client.post(self.endpoint, json=payload)
                response.raise_for_status()
                return response.json()

        try:
            data = call_with_retry(request, self.retry_policy, PROVIDER, self.stop_generation_event)
            final_text = data["choices"][0]["message"]["content"] or ""
        except LLMAPIError as e:
            func.error(f"[{PROVIDER}] {e.user_message()}")
            raise
        except (KeyError, IndexError, TypeError, ValueError) as e:
            err = LLMAPIError(f"unexpected response from {self.endpoint}: {e}", provider=PROVIDER)
            func.error(f"[{PROVIDER}] {err.user_message()}")
            raise err from e
        finally:
            self.trigger(BaseModel.STREAMING_FINISHED_EVENT)

        self.trigger("token", final_text)
        return final_text

    def _open_stream(self, payload: Dict[str, Any]) -> Generator[str, None, None]:
        """One streaming request: yields content chunks from the server's SSE lines."""
        with httpx.stream("POST", self.endpoint, json=payload, timeout=self._timeout()) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if self.stop_generation_event.is_set():
                    return
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:].strip()  # Strip out 'data: ' prefix
                if data_str == "[DONE]":
                    return
                try:
                    chunk_data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                if isinstance(chunk_data, dict) and chunk_data.get("error"):
                    # The server failed mid-generation and reports it in-band.
                    raise LLMAPIError(f"server error: {chunk_data['error']}", provider=PROVIDER)
                try:
                    content = chunk_data["choices"][0]["delta"].get("content", "")
                except (KeyError, IndexError, TypeError, AttributeError):
                    continue
                if content:
                    yield content

    def _run_streaming_chat(self, payload: Dict[str, Any]) -> Generator[str, None, None]:
        """
        Handles streaming lines from the custom FastAPI server.

        Args:
            payload: The request payload containing chat parameters.

        Yields:
            str: A chunk of text content as it is received from the stream.

        Raises:
            LLMAPIError: If the server cannot be reached, answers with an error status,
                or reports an error in the stream.
        """
        full_content = ""
        try:
            for content in stream_with_retry(lambda: self._open_stream(payload), self.retry_policy,
                                             PROVIDER, self.stop_generation_event):
                full_content += content
                self.trigger("token", content)
                yield content
        except LLMAPIError as e:
            e.partial = e.partial or bool(full_content)
            func.error(f"[{PROVIDER}] {e.user_message()}")
            raise
        except Exception as e:
            err = wrap_error(e, PROVIDER, attempts=1, partial=bool(full_content))
            func.error(f"[{PROVIDER}] {err.user_message()}")
            raise err from e
        finally:
            self.trigger(BaseModel.STREAMING_FINISHED_EVENT, full_content)

    def clean_cache(self) -> None:
        """
        Forces garbage collection to clear memory buffers.
        """
        gc.collect()