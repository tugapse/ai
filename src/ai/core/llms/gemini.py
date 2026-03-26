import os
import threading
import io
import gc
import time
import re
from .base_llm import BaseModel, ModelParams 
import functions as func


class GeminiAPIModel(BaseModel):
    """
    Lazy-loading Gemini API implementation of BaseModel.
    Supports multimodal input (text + images) and streaming.
    Designed for 2026 standards with Gemini 2.0/3.0.
    """
    def __init__(self, model_name="gemini-2.0-flash", system_prompt=None, api_key=None, **kargs):
        super().__init__(model_name, system_prompt, **kargs)
        
        # --- LAZY IMPORT ---
        try:
            from google import genai
            from google.genai import types
            self.genai_module = genai
            self.genai_types = types
        except ImportError:
            func.log("ERROR: 'google-genai' package not found.")
            func.log("Please run: pip install google-genai")
            raise ImportError("Missing dependency: google-genai.")

        # API Key Setup
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            func.error("No GEMINI_API_KEY found. API model cannot initialize.")
            raise ValueError("Gemini API Key is required.")
            
        self.client = self.genai_module.Client(api_key=self.api_key)
        
        # Configuration mapping
        model_params = kargs.get('model_params', {}) or {}
        
        config_kwargs = {}
        for param_name, api_name in [
            ('temperature', 'temperature'),
            ('max_new_tokens', 'max_output_tokens'),
            ('top_p', 'top_p'),
            ('top_k', 'top_k'),
            ('presence_penalty', 'presence_penalty'),
            ('frequency_penalty', 'frequency_penalty')
        ]:
            val = model_params.get(param_name, kargs.get(param_name))
            if val is not None:
                config_kwargs[api_name] = val

        if self.system_prompt:
            config_kwargs["system_instruction"] = self.system_prompt
            
        self.config = self.genai_types.GenerateContentConfig(**config_kwargs)

    def _convert_messages_to_api(self, messages: list):
        """Converts internal messages to Gemini 'user'/'model' format."""
        api_history = []
        if not messages:
            return api_history
        for msg in messages:
            if msg['role'] == 'system': continue
            role = "user" if msg['role'] == "user" else "model"
            api_history.append({"role": role, "parts": [{"text": msg['content']}]})
        return api_history

   
    def load_images(self, images: list):
        """Lazy-loads PIL to process images into Gemini Parts."""
        try:
            import PIL.Image
        except ImportError:
            func.error("Pillow not installed. Vision features disabled.")
            return []

        image_parts = []
        for img in images:
            try:
                img_obj = PIL.Image.open(img) if isinstance(img, str) else img
                img_byte_arr = io.BytesIO()
                img_obj.save(img_byte_arr, format='PNG')
                image_parts.append(
                    self.genai_types.Part.from_bytes(
                        data=img_byte_arr.getvalue(),
                        mime_type="image/png"
                    )
                )
            except Exception as e:
                func.error(f"Failed to process image for Gemini: {e}")
        return image_parts

    def chat(self, messages: list, images: list = [], stream: bool = True, options: object = None):
        """Main chat entry point compatible with BaseModel threading."""
        self.stop_generation_event.clear()
        
        history = self._convert_messages_to_api(messages)
        last_turn = history.pop() if history and history[-1]["role"] == "user" else {"parts": [{"text": ""}]}
        prompt_text = last_turn["parts"][0]["text"]

        current_content = [prompt_text]
        if images:
            current_content.extend(self.load_images(images))

        try:
            if stream:
                self._generation_thread = threading.Thread(
                    target=self._run_streaming_chat, 
                    args=(current_content, history)
                )
                self._generation_thread.start()
            else:
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        response = self.client.models.generate_content(
                            model=self.model_name,
                            contents=current_content,
                            config=self.config
                        )
                        return response.text
                    except Exception as e:
                        error_msg = str(e)
                        if "429" in error_msg and "RESOURCE_EXHAUSTED" in error_msg and attempt < max_retries - 1:
                            match = re.search(r"retry in ([\d\.]+)s", error_msg)
                            wait_time = float(match.group(1)) + 2.0 if match else 15.0
                            
                            msg = f"Gemini API rate limit hit. Waiting {wait_time:.1f}s before retry ({attempt+1}/{max_retries})..."
                            func.out(f"\n[ * ] {msg}")
                            func.log(msg, level="WARNING")
                            
                            for _ in range(int(wait_time)):
                                if self.stop_generation_event.is_set(): break
                                time.sleep(1)
                            if not self.stop_generation_event.is_set(): time.sleep(wait_time - int(wait_time))
                            continue
                            
                        if "unexpected model name format" in error_msg:
                            err_text = f"Gemini API Error: Invalid model name '{self.model_name}'. Use a specific model like 'gemini-2.0-flash'."
                            func.error(err_text)
                            return err_text
                        else:
                            func.error(f"Gemini API Error: {e}")
                            return f"Gemini API Error: {e}"
        except Exception as e:
            func.error(f"Gemini Setup Error: {e}")
            return f"Gemini Setup Error: {e}"

    def _run_streaming_chat(self, current_content, history):
        """Background thread for token streaming."""
        full_contents = history + [{"role": "user", "parts": [{"text": c} if isinstance(c, str) else c for c in current_content]}]
        max_retries = 3
        
        try:
            for attempt in range(max_retries):
                try:
                    response_stream = self.client.models.generate_content_stream(
                        model=self.model_name,
                        contents=full_contents,
                        config=self.config
                    )
        
                    for chunk in response_stream:
                        if self.stop_generation_event.is_set():
                            func.log("Generation stopped by user.")
                            return
                        if chunk.text:
                            self.trigger("token", chunk.text)
                    break  # Success, exit retry loop
        
                except Exception as e:
                    error_msg = str(e)
                    if "429" in error_msg and "RESOURCE_EXHAUSTED" in error_msg and attempt < max_retries - 1:
                        match = re.search(r"retry in ([\d\.]+)s", error_msg)
                        wait_time = float(match.group(1)) + 2.0 if match else 15.0
                        
                        msg = f"Gemini API rate limit hit. Waiting {wait_time:.1f}s before retry ({attempt+1}/{max_retries})..."
                        func.out(f"\n[ * ] {msg}")
                        func.log(msg, level="WARNING")
                        self.trigger("token", f"\n[Rate limit reached, waiting {wait_time:.1f}s to retry...]\n")
                        
                        for _ in range(int(wait_time)):
                            if self.stop_generation_event.is_set(): break
                            time.sleep(1)
                        if not self.stop_generation_event.is_set(): time.sleep(wait_time - int(wait_time))
                        
                        if self.stop_generation_event.is_set():
                            break
                        continue  # Retry loop
        
                    if "unexpected model name format" in error_msg:
                        err_text = f"Gemini Stream Error: Invalid model name '{self.model_name}'. Use a specific model like 'gemini-2.0-flash'."
                        func.error(err_text)
                        self.trigger("token", err_text)
                    else:
                        func.error(f"Gemini Stream Error: {e}")
                        self.trigger("token", f"Gemini API Error: {e}")
                    break  # Break on other non-retriable errors
        finally:
            self.trigger(BaseModel.STREAMING_FINISHED_EVENT)

    def is_gpu_available(self): return False
    def clean_cache(self): gc.collect()