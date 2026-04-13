import json
import requests
import functions as func
from core.llms.base_llm import BaseModel, ModelParams
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
        self.inference_device = InferenceBackend.GPU_CUDA # We assume the Remote Brain is GPU-powered
        
    def chat(self, messages: list, images: list = None, stream: bool = True, options: dict = {}):
        """
        Sends the context to the Main PC and yields tokens as they arrive.
        """
        endpoint = f"{self.url}/v1/chat"
        
        payload = {
            "model_id": self.model_id,
            "messages": messages,
            "system_prompt": self.system_prompt,
            "stream": stream,
            "options": options
        }

        try:
            # We use stream=True in requests to handle the token chunks
            response = requests.post(endpoint, json=payload, stream=True, timeout=120)
            response.raise_for_status()

            for line in response.iter_lines():
                if not line:
                    continue
                
                # Parse the NDJSON (Newline Delimited JSON) from the server
                chunk = json.loads(line.decode('utf-8'))
                
                # 1. Update the local Fuel Gauge with stats from the Brain
                if "stats" in chunk:
                    s = chunk["stats"]
                    self.token_info_count.prompt_count = s.get("prompt_count", 0)
                    self.token_info_count.total_prompt_count = s.get("total_tokens", 0)
                    self.token_info_count.printed_tokens_count = s.get("output_tokens", 0)
                    self.token_info_count.max_context_window = s.get("window", 0)

                # 2. Yield the text token to the UI
                if "token" in chunk:
                    yield chunk["token"]

                # 3. Check for local interruption (Ctrl+C)
                if self.stop_generation_event.is_set():
                    func.log("Remote: Interruption detected. Signaling server...")
                    self.request_shutdown()
                    break

        except requests.exceptions.RequestException as e:
            func.error(f"Neural Link Lost: {e}")
            yield f"\n[ERROR: Could not connect to Brain at {self.url}]"

    def request_shutdown(self):
        """
        Tells the Main PC to stop thinking and release VRAM.
        """
        self.stop_generation_event.set()
        try:
            requests.post(f"{self.url}/v1/shutdown", timeout=5)
            func.log("Remote Brain: Generation halted.")
        except:
            pass
        finally:
            self.stop_generation_event.clear()

    def list(self):
        """Asks the server what other brains are available."""
        try:
            r = requests.get(f"{self.url}/models")
            return r.json().get("models", [])
        except:
            return []