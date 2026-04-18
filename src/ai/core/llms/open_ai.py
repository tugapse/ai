import os
import threading
import gc
from typing import Dict, List, Any, Optional, Union, Generator

from .base_llm import BaseModel
import functions as func


class OpenAIAPIModel(BaseModel):
    """
    A generalized, OpenAI-compatible API interface for Just A Reasoning Virtual Intelligent Sentinel (JARVIS).
    
    This class handles standard text generation, native streaming tool calls (via an internal accumulator),
    and real-time telemetry tracking across any provider implementing the OpenAI specification 
    (OpenAI, Azure AI Foundry, Mistral, Ollama, vLLM, etc.).
    """

    def __init__(self, model_name: Optional[str] = None, system_prompt: Optional[str] = None, api_key: Optional[str] = None, **kargs: Any):
        """
        Initializes the OpenAI API model interface.

        Args:
            model_name (str, optional): The name of the model or Azure deployment. Defaults to env var 'AI_MODEL_NAME' or 'gpt-4o'.
            system_prompt (str, optional): The system prompt to inject into the conversation.
            api_key (str, optional): The API key for the provider. Defaults to env var 'AI_API_KEY'.
            **kargs: Additional configuration parameters (e.g., base_url, api_version, azure_endpoint, max_new_tokens).
            
        Raises:
            ImportError: If the 'openai' Python package is not installed.
        """
        model_name = model_name or os.environ.get("AI_MODEL_NAME", "gpt-4o")
        super().__init__(model_name, system_prompt, **kargs)
        
        try:
            from openai import OpenAI, AzureOpenAI
            self._OpenAIClient = OpenAI
            self._AzureClient = AzureOpenAI
        except ImportError:
            func.log("ERROR: 'openai' package not found.")
            raise ImportError("Please install the requirement: pip install openai")

        self.api_key = api_key or os.environ.get("AI_API_KEY")
        self.base_url = kargs.get("base_url")
        self.api_version = kargs.get("api_version") or os.environ.get("AI_API_VERSION")
        self.azure_endpoint = kargs.get("azure_endpoint") or os.environ.get("AI_AZURE_ENDPOINT")

        # Client instantiation based on Azure vs Standard OpenAI routing
        if self.azure_endpoint:
            func.log(f"JARVIS: Connecting to Azure Interface [{self.model_name}]")
            self.client = self._AzureClient(
                azure_endpoint=self.azure_endpoint,
                api_key=self.api_key,
                api_version=self.api_version or "2024-05-01-preview"
            )
        else:
            func.log(f"JARVIS: Connecting to OpenAI-Compatible Interface [{self.model_name}]")
            self.client = self._OpenAIClient(
                api_key=self.api_key,
                base_url=self.base_url 
            )
        
        # Determine model parameters dynamically based on reasoning capabilities
        self.options: Dict[str, Any] = {}
        is_reasoning_model = any(keyword in self.model_name.lower() for keyword in ["o1-", "o1", "nano", "reasoning"])

        if is_reasoning_model:
            self.options["max_completion_tokens"] = kargs.get('max_new_tokens', 2048)
        else:
            self.options["max_tokens"] = kargs.get('max_new_tokens', 2048)
            self.options["temperature"] = kargs.get('temperature', 0.5)
            self.options["top_p"] = kargs.get('top_p', 0.95)
            self.options["presence_penalty"] = kargs.get('presence_penalty', 0.0)
            self.options["frequency_penalty"] = kargs.get('frequency_penalty', 0.0)

        # Telemetry Initialization
        out_tokens = self.options.get("max_completion_tokens") or self.options.get("max_tokens") or 2048
        self.token_info_count.max_output_tokens = out_tokens
        self.token_info_count.max_context_window = kargs.get("n_ctx", BaseModel.CONTEXT_WINDOW_128K)

    def _convert_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Formats internal message dictionaries into the standard OpenAI message schema.

        Args:
            messages (List[Dict[str, str]]): The internal conversation history.

        Returns:
            List[Dict[str, str]]: The formatted conversation history, including the system prompt.
        """
        formatted = []
        if self.system_prompt:
            formatted.append({"role": "system", "content": self.system_prompt})
            
        for msg in messages:
            if msg['role'] == 'system': 
                continue
            formatted.append({"role": msg['role'], "content": msg['content']})
        return formatted

    def chat(self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None, stream: bool = True, options: Optional[Dict[str, Any]] = None) -> Union[str, Dict[str, Any], Generator[Union[str, Dict[str, Any]], None, None]]:
        """
        Executes a chat completion request to the configured API provider.

        Args:
            messages (List[Dict[str, str]]): The conversation history.
            tools (List[Dict[str, Any]], optional): A list of JSON schemas defining available tools.
            stream (bool, optional): If True, yields a generator for streaming responses. Defaults to True.
            options (Dict[str, Any], optional): Additional runtime overrides.

        Returns:
            Union[str, Dict[str, Any], Generator]: 
                - If stream=True: Returns a Generator yielding string tokens or a Tool Call Dictionary.
                - If stream=False: Returns a complete string response or a Tool Call Dictionary.
        """
        self.stop_generation_event.clear()
        formatted_msgs = self._convert_messages(messages)

        request_kwargs = {**self.options}
        if tools:
            request_kwargs["tools"] = tools

        try:
            if stream:
                return self._run_streaming_chat(formatted_msgs, tools)
            else:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=formatted_msgs,
                    stream=False,
                    **request_kwargs # type: ignore
                )
                
                # Telemetry Update
                if hasattr(response, 'usage') and response.usage:
                    self._update_token_metrics(response.usage)

                choice = response.choices[0]
                
                # Intercept synchronous tool calls
                if choice.message.tool_calls:
                    self.trigger(BaseModel.STREAMING_FINISHED_EVENT)
                    return {"type": "tool_calls", "data": choice.message.tool_calls}
                
                final_text = choice.message.content or ""
                self.trigger("token", final_text)
                self.trigger(BaseModel.STREAMING_FINISHED_EVENT)
                return final_text
                
        except Exception as e:
            func.error(f"Interface Error: {e}")
            self.trigger(BaseModel.STREAMING_FINISHED_EVENT)
            return ""

    def _run_streaming_chat(self, formatted_msgs: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None) -> Generator[Union[str, Dict[str, Any]], None, None]:
        """
        Handles the streaming logic, including telemetry retrieval and tool call fragment accumulation.

        Args:
            formatted_msgs (List[Dict[str, str]]): The formatted conversation history.
            tools (List[Dict[str, Any]], optional): A list of JSON schemas defining available tools.

        Yields:
            Union[str, Dict[str, Any]]: Individual string tokens, system messages, or a fully assembled tool call dictionary.
        """
        request_kwargs = {**self.options}
        if tools:
            request_kwargs["tools"] = tools

        # Request telemetry data in the final chunk
        request_kwargs["stream_options"] = {"include_usage": True}

        accumulated_tool_calls: Dict[int, Dict[str, Any]] = {}

        try:
            stream = self.client.chat.completions.create(
                model=self.model_name,
                messages=formatted_msgs,
                stream=True,
                **request_kwargs # type: ignore
            )

            for chunk in stream:
                if self.stop_generation_event.is_set():
                    break
                
                # Telemetry Update (typically arrives in the final chunk)
                if hasattr(chunk, 'usage') and chunk.usage:
                    self._update_token_metrics(chunk.usage)
                
                if chunk.choices and len(chunk.choices) > 0:
                    choice = chunk.choices[0]
                    
                    # 1. Yield Standard Text Tokens
                    if choice.delta.content:
                        content = choice.delta.content
                        self.trigger("token", content)
                        yield content  
                    
                    # 2. Accumulate Tool Call Fragments
                    if choice.delta.tool_calls:
                        for tool_chunk in choice.delta.tool_calls:
                            idx = tool_chunk.index
                            
                            if idx not in accumulated_tool_calls:
                                accumulated_tool_calls[idx] = {
                                    "id": tool_chunk.id,
                                    "type": "function",
                                    "function": {
                                        "name": tool_chunk.function.name or "",
                                        "arguments": ""
                                    }
                                }
                            
                            if tool_chunk.function and tool_chunk.function.arguments:
                                accumulated_tool_calls[idx]["function"]["arguments"] += tool_chunk.function.arguments

                    # 3. Handle Stream Termination
                    finish_reason = choice.finish_reason
                    if finish_reason:
                        if finish_reason == "tool_calls":
                            assembled_tools = list(accumulated_tool_calls.values())
                            self.trigger("tool_call", assembled_tools)
                            yield {"type": "tool_calls", "data": assembled_tools}
                            
                        elif finish_reason == "length":
                            error_msg = "\n\n[SYSTEM: Transmission truncated. Max tokens reached.]"
                            self.trigger("token", error_msg)
                            yield error_msg
                        elif finish_reason == "content_filter":
                            error_msg = "\n\n[SYSTEM: Azure Content Filter blocked the transmission.]"
                            self.trigger("token", error_msg)
                            yield error_msg
                        elif finish_reason != "stop":
                            error_msg = f"\n\n[SYSTEM: Stream ended. Reason: {finish_reason}]"
                            self.trigger("token", error_msg)
                            yield error_msg

        except Exception as e:
            func.error(f"Interface Stream Error [{type(e).__name__}]: {e}")
        finally:
            self.trigger(BaseModel.STREAMING_FINISHED_EVENT)

    def _update_token_metrics(self, usage: Any) -> None:
        """
        Updates the internal telemetry tracker with the latest usage data from the API.

        Args:
            usage (Any): The API response usage object containing prompt and completion token counts.
        """
        self.token_info_count.prompt_count = usage.prompt_tokens
        self.token_info_count.printed_tokens_count = usage.completion_tokens
        self.token_info_count.total_prompt_count = usage.total_tokens
        func.debug(f"[OPENAI Engine] Metrics Updated: {self.token_info_count.get_log_string()}")

    def clean_cache(self) -> None:
        """Forces garbage collection to clear memory buffers."""
        gc.collect()