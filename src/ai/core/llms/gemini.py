import os
import threading
import io
import gc
import time
import re
import subprocess
import warnings
import json

# Silencia o aviso de depreciação do Vertex AI
warnings.filterwarnings(
    "ignore", 
    message=".*This feature is deprecated as of June 24, 2025.*", 
    category=UserWarning
)

from .base_llm import BaseModel, ModelParams 
import functions as func
from color import Color

class GeminiAPIModel(BaseModel):
    def __init__(self, model_name="gemini-2.5-flash", system_prompt=None, api_key=None, use_vertex=True, project_id=None, location="us-central1", **kargs):
        func.log(f"Initializing GeminiAPIModel for model: {model_name}")
        
        super().__init__(model_name, system_prompt, **kargs)
        self.use_vertex = use_vertex
        
        if self.use_vertex:
            if not self._check_gcp_auth():
                func.error("Google Cloud Auth não encontrada!")
                raise PermissionError("Autenticação Google Cloud (ADC) necessária.")
            
            try:
                import vertexai
                # Removed native Tool and FunctionDeclaration imports. Using pure text processing.
                from vertexai.generative_models import GenerativeModel, Part, GenerationConfig
                self.project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT") 
                vertexai.init(project=self.project_id, location=location)
                
                self.config_class = GenerationConfig
                self.part_class = Part
                func.log(f"Vertex AI Setup concluído para {self.model_name}", level="DEBUG")
            except ImportError:
                func.error("Missing 'google-cloud-aiplatform'.")
                raise
        else:
            from google import genai
            self.client = genai.Client(api_key=api_key or os.environ.get("GEMINI_API_KEY"))

        model_params = kargs.get('model_params', {}) or {}
        self.config_kwargs = {}
        self.token_info_count.max_context_window = model_params.get('n_ctx', self.CONTEXT_WINDOW_1M)

        for param, api_param in [('temperature', 'temperature'), ('max_new_tokens', 'max_output_tokens'), ('top_p', 'top_p'), ('top_k', 'top_k')]:
            val = model_params.get(param, kargs.get(param))
            if val is not None: self.config_kwargs[api_param] = val

    # NOTE: We DO NOT override format_tools_for_prompt() here anymore.
    # It will inherit from BaseModel and inject the text manual!

    def _convert_messages_to_api(self, messages: list):
        """Converte o histórico para o formato Vertex AI, forçando a estrutura de texto puro do J.A.R.V.I.S."""
        if not messages or not self.use_vertex: return []
        from vertexai.generative_models import Content, Part

        api_messages = []
        for m in messages:
            role = m.get('role')
            if role == 'system': continue

            # 1. TOOL RESULT FLATTENING
            # Converts the Orchestrator's tool result into a plain text USER message
            if role in ['tool', 'function']:
                text = f"[SYSTEM RESULT FOR TOOL '{m.get('name', 'unknown')}']\n{m.get('content')}"
                if api_messages and api_messages[-1].role == "user":
                    api_messages[-1].parts.append(Part.from_text(f"\n{text}"))
                else:
                    api_messages.append(Content(role="user", parts=[Part.from_text(text)]))
                continue

            # 2. TOOL CALL FLATTENING
            # Converts previous tool calls into the literal text the model would have generated
            if role == 'assistant' and m.get('tool_calls'):
                for call in m['tool_calls']:
                    name = call['function']['name']
                    args = call['function']['arguments']
                    args_str = json.dumps(args) if isinstance(args, dict) else args
                    text = f"____@tool call:{name}{args_str}"
                    
                    if api_messages and api_messages[-1].role == "model":
                        api_messages[-1].parts.append(Part.from_text(f"\n{text}"))
                    else:
                        api_messages.append(Content(role="model", parts=[Part.from_text(text)]))
                continue

            # 3. STANDARD TEXT
            if m.get('content'):
                v_role = "user" if role == "user" else "model"
                
                # Vertex AI strictly requires alternating roles (User->Model->User).
                # This merges consecutive messages of the same role to prevent API crashes.
                if api_messages and api_messages[-1].role == v_role:
                    api_messages[-1].parts.append(Part.from_text(f"\n{m.get('content')}"))
                else:
                    api_messages.append(Content(role=v_role, parts=[Part.from_text(m.get('content'))]))
            
        return api_messages

    def chat(self, messages: list, images: list = [], stream: bool = True, options: dict = None):
        self.stop_generation_event.clear()
        
        dynamic_system_prompt = self.system_prompt
        for m in messages:
            if m.get('role') == 'system':
                dynamic_system_prompt = m.get('content')
                break
        
        if dynamic_system_prompt:
            dynamic_system_prompt = f"{self.get_system_info()}\n{dynamic_system_prompt}"

        history = self._convert_messages_to_api(messages)
        self._append_images_to_history(history, images)

        current_options = self.config_kwargs.copy()
        
        if options:
            if 'max_tokens' in options: current_options['max_output_tokens'] = options['max_tokens']
            if 'temperature' in options: current_options['temperature'] = options['temperature']
            if 'top_p' in options: current_options['top_p'] = options['top_p']
            if 'top_k' in options: current_options['top_k'] = options['top_k']

        func.debug(f"Gemini Processing {len(history)} messages (Pure Text Protocol) | Stream: {stream}")
        
        if stream:
            return self._stream_generator(history, dynamic_system_prompt, current_options)
        return self._generate_response_sync(history, dynamic_system_prompt, current_options)

    def _stream_generator(self, history, dynamic_system_prompt, current_options):
        full_content = ""
        sentinel_buffer = ""
        is_intercepting = False
        
        try:
            from vertexai.generative_models import GenerativeModel
            model = GenerativeModel(self.model_name, system_instruction=[dynamic_system_prompt] if dynamic_system_prompt else None)
            
            responses = model.generate_content(
                history, 
                stream=True, 
                generation_config=self.config_class(**current_options)
            )
            
            for r in responses:
                if self.stop_generation_event.is_set(): break
                
                try:
                    content = r.text
                except Exception:
                    continue
                    
                if not content: continue
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

            if is_intercepting and sentinel_buffer:
                self.trigger("token", sentinel_buffer)
                yield sentinel_buffer

        except Exception as e:
            func.error(f"Stream Loop Error: {e}")
            yield f"Error: {e}"
        finally:
            self.trigger(BaseModel.STREAMING_FINISHED_EVENT, full_content)

    def _generate_response_sync(self, history, dynamic_system_prompt, current_options):
        from vertexai.generative_models import GenerativeModel
        model = GenerativeModel(self.model_name, system_instruction=[dynamic_system_prompt] if dynamic_system_prompt else None)
        resp = model.generate_content(history, generation_config=self.config_class(**current_options))
        
        try:
            text = resp.text
        except Exception:
            text = ""
            
        action = self.parse_manual_tags(text)
        return action if action else text

    def _check_gcp_auth(self):
        if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"): return True
        paths = [
            os.path.expanduser('~/.config/gcloud/application_default_credentials.json'),
            os.path.join(os.environ.get('APPDATA', ''), 'gcloud', 'application_default_credentials.json') if os.name == 'nt' else ''
        ]
        if any(os.path.exists(p) for p in paths if p): return True
        try:
            return subprocess.run(["gcloud", "auth", "print-access-token"], capture_output=True, timeout=5).returncode == 0
        except: return False

    def load_images(self, images: list):
        image_parts = []
        for img in images:
            try:
                import PIL.Image
                img_obj = PIL.Image.open(img) if isinstance(img, str) else img
                img_byte_arr = io.BytesIO()
                img_obj.save(img_byte_arr, format='PNG')
                image_parts.append(self.part_class.from_data(data=img_byte_arr.getvalue(), mime_type="image/png"))
            except Exception as e:
                func.error(f"Image Error: {e}")
        return image_parts

    def _append_images_to_history(self, history, images):
        if not images or not history: return
        image_parts = self.load_images(images)
        for content in reversed(history):
            if content.role == "user":
                content.parts.extend(image_parts)
                break

    def is_gpu_available(self): return False
    def clean_cache(self): gc.collect()