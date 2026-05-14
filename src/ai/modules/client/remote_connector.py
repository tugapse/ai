import json
import requests
from typing import Any
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
        self.inference_device = InferenceBackend.GPU_CUDA 
        
    def check_system_prompt(self, messages: Any) -> Any:
        return messages

    def chat(self, messages: list, images: list = None, stream: bool = False, options: dict = {}):
        messages = self.check_system_prompt(messages)
        
        endpoint = f"{self.url}/api/v1/chat/completions"
        payload = {
            "model": self.model_id,
            "messages": messages,
            "stream": stream,
            "temperature": options.get("temperature", 0.7),
            "system_prompt": self.system_prompt,
            "model_params": self.options
        }

        try:
            # The stream=stream parameter in requests is crucial here
            response = requests.post(endpoint, json=payload, stream=stream, timeout=120)
            response.raise_for_status()
            
            # --- NEW STREAM READING LOGIC ---
            if stream:
                # iter_lines() reads the response chunk by chunk as it arrives
                for line in response.iter_lines():
                    if line:

                        decoded_line = line.decode('utf-8')
                        func.log(decoded_line, level="WARN")
                        # Parse standard SSE format
                        if decoded_line.startswith("data: "):
                            data_str = decoded_line[6:] # Strip 'data: ' prefix
                            
                            if data_str == "[DONE]":
                                break
                                
                            try:
                                chunk_data = json.loads(data_str)
                                
                                # Catch server-side streaming errors
                                if "error" in chunk_data:
                                    yield f"\n[Brain Error: {chunk_data['error']}]"
                                    break
                                
                                # Extract the delta chunk
                                if "choices" in chunk_data and len(chunk_data["choices"]) > 0:
                                    delta = chunk_data["choices"][0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        yield content
                            except json.JSONDecodeError:
                                pass # Ignore incomplete JSON lines
            
            # --- FALLBACK FOR NON-STREAMING ---
            else:
                data = response.json()
                if "choices" in data and len(data["choices"]) > 0:
                    content = data["choices"][0]["message"]["content"]
                    
                    if not isinstance(content, str):
                        if isinstance(content, list) and len(content) == 0:
                            content = "... (Brain sent an empty response) ..."
                        else:
                            content = str(content)
                    yield content
                else:
                    yield "[ ! ] Brain Error: Empty choices list."

        except Exception as e:
            yield f"\n[LINK ERROR: {str(e)}]"

    def request_shutdown(self):
        self.stop_generation_event.set()
        try:
            requests.post(f"{self.url}/v1/shutdown", timeout=5)
        except:
            pass
        finally:
            self.stop_generation_event.clear()

    def list(self):
        try:
            r = requests.get(f"{self.url}/health")
            return [r.json().get("model", "Default Brain")]
        except:
            return []