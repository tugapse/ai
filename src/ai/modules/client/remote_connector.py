import json
import requests
from typing import Any  # <--- Added this to fix the 'Any' is not defined error
import functions as func
from core.llms.base_llm import BaseModel
from entities.model_enums import InferenceBackend

class RemoteBrainConnector(BaseModel):
    """
    The 'Link' between the Tiny PC and the Main PC.
    Implements the BaseModel interface but executes via API.
    """
    def __init__(self, url: str, model_id: str = "default", **kwargs):
        super().__init__(model_name=model_id, **kwargs)
        self.url = url.rstrip('/')
        self.model_id = model_id
        # The Remote Brain (Main PC) is the one with the heavy lifting
        self.inference_device = InferenceBackend.GPU_CUDA 
        
    def check_system_prompt(self, messages: Any) -> Any:
        """
        FIX: Overrides the base class normalization to allow lists to pass
        through to the server without crashing the client.
        """
        return messages

    def chat(self, messages: list, images: list = None, stream: bool = False, options: dict = {}):
        """
        Sends context to the Main PC and yields a guaranteed STRING.
        """
        # 1. Skip base class normalization to prevent crashes here
        messages = self.check_system_prompt(messages)
        
        endpoint = f"{self.url}/v1/chat/completions"
        payload = {
            "model": self.model_id, # This is our 'parameter'
            "messages": messages,
            "stream": stream,
            "temperature": options.get("temperature", 0.7),
            "system_prompt":self.system_prompt,
            "model_params":self.options
        }

        try:
            response = requests.post(endpoint, json=payload, stream=False, timeout=120)
            response.raise_for_status()
            data = response.json()
            
            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"]
                
                # --- TYPE ENFORCEMENT START ---
                # If the brain sent a list [] or any non-string, we force it to a string.
                if not isinstance(content, str):
                    if isinstance(content, list) and len(content) == 0:
                        content = "... (Brain sent an empty response) ..."
                    else:
                        content = str(content)
                
                # We yield the final string so your UI's normalize() sees a string
                yield content
                # --- TYPE ENFORCEMENT END ---
                
            else:
                yield "[ ! ] Brain Error: Empty choices list."

        except Exception as e:
            # Catching the crash here and yielding a string error message
            yield f"\n[LINK ERROR: {str(e)}]"

    def request_shutdown(self):
        """
        Tells the Main PC to stop thinking and release VRAM.
        """
        self.stop_generation_event.set()
        try:
            # Matches the new /v1/shutdown route in app.py
            requests.post(f"{self.url}/v1/shutdown", timeout=5)
        except:
            pass
        finally:
            self.stop_generation_event.clear()

    def list(self):
        """Asks the server what other brains are available."""
        try:
            r = requests.get(f"{self.url}/health")
            return [r.json().get("model", "Default Brain")]
        except:
            return []