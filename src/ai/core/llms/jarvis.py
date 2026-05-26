import os
import gc
import json
from typing import Dict, List, Any, Optional, Union, Generator
import httpx

import ai.functions as func
from ai.core.llms.base_llm import BaseModel


class JarvisAiModel(BaseModel):
    """
    A drop-in client interface tailored for the JARVIS custom FastAPI endpoint.
    
    Maintains identical structure and event signaling to seamlessly interface 
    with the existing Orchestrator and Sentinel protocols.
    """

    def __init__(self, model_name: Optional[str] = None, system_prompt: str = "", api_key: Optional[str] = None, **kargs: Any):
        """Initializes the custom API endpoint model interface."""
        model_name = model_name or os.environ.get("AI_MODEL_NAME", "gpt-4o")
        super().__init__(model_name, system_prompt, **kargs)
        
        # Configuration routing pointing to the custom backend server
        self.base_url = kargs.get("base_url") or os.environ.get("AI_API_BASE_URL", "http://127.0.0.1:8000")
        self.endpoint = f"{self.base_url.rstrip('/')}/api/v1/chat/completions"
        
        # Session state details used by ChatSessionRouter on the backend
        self.session_id = kargs.get("session_id")
        self.session_folder = kargs.get("session_folder")
        
        func.log(f"JARVIS: Connecting to Custom Backend Interface [{self.model_name}] -> {self.endpoint}")
        
        # Match standard token info context structural tracking
        out_tokens = kargs.get('max_new_tokens', 2048)
        self.token_info_count.max_output_tokens = out_tokens
        self.token_info_count.max_context_window = kargs.get("n_ctx", BaseModel.CONTEXT_WINDOW_128K)

    def chat(self, messages: List[Dict[str, str]], images=[],stream: bool = True, options={} ) -> Union[str, Dict[str, Any], Generator[Union[str, Dict[str, Any]], None, None]]:
        """Executes a chat completion request directly to the custom backend endpoint."""
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
            "model": self.model_name,
            "system_prompt_content": self.system_prompt,
            "stream": stream,
            "session_id": self.session_id,
            "session_folder": self.session_folder,
            "messages": messages
        }

        try:
            if stream:
                return self._run_streaming_chat(payload)
            else:
                with httpx.Client(timeout=60.0) as client:
                    response = client.post(self.endpoint, json=payload)
                    response.raise_for_status()
                    data = response.json()
                    
                    final_text = data["choices"][0]["message"]["content"] or ""
                    
                    self.trigger("token", final_text)
                    self.trigger(BaseModel.STREAMING_FINISHED_EVENT)
                    return final_text
                
        except Exception as e:
            func.error(f"Interface Custom Endpoint Error: {e}")
            self.trigger(BaseModel.STREAMING_FINISHED_EVENT)
            return ""

    def _run_streaming_chat(self, payload: Dict[str, Any]) -> Generator[str, None, None]:
        """Handles streaming lines from the custom FastAPI server."""
        full_content = ""
        
        try:
            with httpx.stream("POST", self.endpoint, json=payload, timeout=60.0) as response:
                response.raise_for_status()
                
                for line in response.iter_lines():
                    if self.stop_generation_event.is_set():
                        break
                        
                    if not line or not line.startswith("data: "):
                        continue
                        
                    data_str = line[6:].strip() # Strip out 'data: ' prefix
                    if data_str == "[DONE]":
                        break
                        
                    try:
                        chunk_data = json.loads(data_str)
                        content = chunk_data["choices"][0]["delta"].get("content", "")
                        
                        if content:
                            full_content += content
                            self.trigger("token", content)
                            yield content
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue

        except Exception as e:
            func.error(f"Interface Custom Stream Error: {e}")
        finally:
            self.trigger(BaseModel.STREAMING_FINISHED_EVENT, full_content)

    def clean_cache(self) -> None:
        """Forces garbage collection to clear memory buffers."""
        gc.collect()