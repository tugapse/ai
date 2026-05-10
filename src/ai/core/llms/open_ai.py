import os
import threading
import gc
import json
from typing import Dict, List, Any, Optional, Union, Generator

from .base_llm import BaseModel
import functions as func
from color import Color


class OpenAIAPIModel(BaseModel):
    """
    A generalized, OpenAI-compatible API interface for Just A Reasoning Virtual Intelligent Sentinel (JARVIS).
    
    This class handles standard text generation, pure text-based streaming tool calls (via Sentinel interception),
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

    # NOTE: Inheriting format_tools_for_prompt() from BaseModel to inject the ____@tool text protocol.

    def _convert_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Formats internal message dictionaries into the standard OpenAI message schema,
        flattening tool calls and results into pure text to enforce the agnostic protocol.

        Args:
            messages (List[Dict[str, str]]): The internal conversation history.

        Returns:
            List[Dict[str, str]]: The formatted pure-text conversation history.
        """
        formatted = []
        if self.system_prompt:
            formatted.append({"role": "system", "content": self.system_prompt})
            
        for msg in messages:
            role = msg.get('role')
            if role == 'system': 
                continue

            # 1. TOOL RESULT FLATTENING
            if role in ['tool', 'function']:
                text = f"[SYSTEM RESULT FOR TOOL '{msg.get('name', 'unknown')}']\n{msg.get('content')}"
                formatted.append({"role": "user", "content": text})
                continue

            # 2. TOOL CALL FLATTENING
            if role == 'assistant' and msg.get('tool_calls'):
                for call in msg['tool_calls']:
                    name = call['function']['name']
                    args = call['function']['arguments']
                    args_str = json.dumps(args) if isinstance(args, dict) else args
                    text = f"____@tool call:{name}{args_str}"
                    formatted.append({"role": "assistant", "content": text})
                continue

            # 3. STANDARD TEXT
            formatted.append({"role": role, "content": msg.get('content', '')})

        return formatted

    def chat(self, messages: List[Dict[str, str]], tools: Optional[List[Dict[str, Any]]] = None, stream: bool = True, options: Optional[Dict[str, Any]] = None) -> Union[str, Dict[str, Any], Generator[Union[str, Dict[str, Any]], None, None]]:
        """
        Executes a pure-text chat completion request to the configured API provider.
        Native API tool passing is deliberately bypassed to enforce the Sentinel Protocol.
        """
        self.stop_generation_event.clear()
        
        # Check if the Orchestrator passed dynamic context
        dynamic_system_prompt = self.system_prompt
        for m in messages:
            if m.get('role') == 'system':
                dynamic_system_prompt = m.get('content')
                break
        
        if dynamic_system_prompt:
            self.system_prompt = dynamic_system_prompt

        formatted_msgs = self._convert_messages(messages)
        request_kwargs = {**self.options}

        try:
            if stream:
                return self._run_streaming_chat(formatted_msgs)
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
                final_text = choice.message.content or ""
                
                # Intercept synchronous text-based tool calls using the BaseModel parser
                action = self.parse_manual_tags(final_text)
                if action:
                    self.trigger(BaseModel.STREAMING_FINISHED_EVENT)
                    return action
                
                self.trigger("token", final_text)
                self.trigger(BaseModel.STREAMING_FINISHED_EVENT)
                return final_text
                
        except Exception as e:
            func.error(f"Interface Error: {e}")
            self.trigger(BaseModel.STREAMING_FINISHED_EVENT)
            return ""

    def _run_streaming_chat(self, formatted_msgs: List[Dict[str, str]]) -> Generator[Union[str, Dict[str, Any]], None, None]:
        """
        Handles the streaming logic, including telemetry retrieval and Sentinel text interception.
        """
        request_kwargs = {**self.options}
        request_kwargs["stream_options"] = {"include_usage": True}

        sentinel_buffer = ""
        is_intercepting = False
        full_content = ""

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
                
                # Telemetry Update
                if hasattr(chunk, 'usage') and chunk.usage:
                    self._update_token_metrics(chunk.usage)
                
                if chunk.choices and len(chunk.choices) > 0:
                    choice = chunk.choices[0]
                    content = choice.delta.content

                    if content:
                        full_content += content
                        
                        # --- UNIVERSAL SENTINEL INTERCEPTION ---
                        out, sentinel_buffer, is_intercepting, should_stop = self.handle_sentinel(
                            content, is_intercepting, sentinel_buffer
                        )
                        
                        if out:
                            if isinstance(out, dict) and out.get("type") == "function_call":
                                func.log(f"{Color.CYAN}[SENTINEL]: TEXT ACTION DETECTED -> {out['name']}{Color.RESET}")
                                self.trigger("tool_detected", out["name"])
                                yield out
                                return
                            else:
                                self.trigger("token", out)
                                yield out
                        
                        if should_stop:
                            break

                    # Handle Stream Termination
                    finish_reason = choice.finish_reason
                    if finish_reason and finish_reason not in ["stop", "tool_calls"]:
                        if finish_reason == "length":
                            error_msg = "\n\n[SYSTEM: Transmission truncated. Max tokens reached.]"
                        elif finish_reason == "content_filter":
                            error_msg = "\n\n[SYSTEM: Content Filter blocked the transmission.]"
                        else:
                            error_msg = f"\n\n[SYSTEM: Stream ended. Reason: {finish_reason}]"
                            
                        self.trigger("token", error_msg)
                        yield error_msg

            if is_intercepting and sentinel_buffer:
                self.trigger("token", sentinel_buffer)
                yield sentinel_buffer

        except Exception as e:
            func.error(f"Interface Stream Error [{type(e).__name__}]: {e}")
        finally:
            self.trigger(BaseModel.STREAMING_FINISHED_EVENT, full_content)

    def _update_token_metrics(self, usage: Any) -> None:
        """
        Updates the internal telemetry tracker with the latest usage data from the API.
        """
        self.token_info_count.prompt_count = usage.prompt_tokens
        self.token_info_count.printed_tokens_count = usage.completion_tokens
        self.token_info_count.total_prompt_count = usage.total_tokens
        func.debug(f"[OPENAI Engine] Metrics Updated: {self.token_info_count.get_log_string()}")

    def clean_cache(self) -> None:
        """Forces garbage collection to clear memory buffers."""
        gc.collect()