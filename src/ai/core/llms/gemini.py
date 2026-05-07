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
                from vertexai.generative_models import GenerativeModel, Part, GenerationConfig, Tool, FunctionDeclaration
                self.project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT") 
                vertexai.init(project=self.project_id, location=location)
                
                self.config_class = GenerationConfig
                self.part_class = Part
                self.tool_class = Tool
                self.func_decl_class = FunctionDeclaration
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

    @staticmethod
    def get_test_tools():
        return [{
            "function_declarations": [
                {
                    "name": "manage_server_module",
                    "description": "Checks status or controls the JARVIS server module (start, stop, restart, status).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "action": {"type": "string", "enum": ["start", "stop", "restart", "status"]}
                        },
                        "required": ["action"]
                    }
                }
            ]
        }]

    def _prepare_vertex_tools(self, tools_list):
        if not tools_list or not self.use_vertex: return None
        from vertexai.generative_models import Tool, FunctionDeclaration
        vertex_tools = []
        for tool_dict in tools_list:
            decls = []
            for decl in tool_dict.get("function_declarations", []):
                func.log(f"DEBUG: Wrapping tool: {decl['name']}", level="DEBUG")
                decls.append(FunctionDeclaration(**decl))
            if decls: vertex_tools.append(Tool(function_declarations=decls))
        return vertex_tools

    def _convert_messages_to_api(self, messages: list):
        """Converte o histórico para o formato Vertex AI, garantindo papéis e tipos corretos."""
        if not messages or not self.use_vertex: return []
        from vertexai.generative_models import Content, Part

        api_messages = []
        for m in messages:
            role = m.get('role')
            if role == 'system': continue

            parts = []
            
            # 1. FUNCTION/TOOL RESPONSE (Result from Orchestrator)
            if role in ['tool', 'function']:
                parts.append(Part.from_function_response(
                    name=m.get('name'),
                    response={"result": m.get('content')} 
                ))
                api_messages.append(Content(role="function", parts=parts))
                continue

            # 2. ASSISTANT WITH TOOL CALLS (The fix is here!)
            if role == 'assistant' and m.get('tool_calls'):
                for call in m['tool_calls']:
                    args = call['function']['arguments']
                    if isinstance(args, str): args = json.loads(args)
                    
                    # SDK Workaround: Use from_dict instead of from_function_call
                    parts.append(Part.from_dict({
                        "function_call": {
                            "name": call['function']['name'],
                            "args": args
                        }
                    }))
                api_messages.append(Content(role="model", parts=parts))
                continue

            # 3. STANDARD TEXT (User or Assistant)
            if m.get('content'):
                parts.append(Part.from_text(m.get('content')))
            
            if parts:
                api_messages.append(Content(role="user" if role == "user" else "model", parts=parts))
            
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

        raw_tools = options.get('tools') if options else None
        if not raw_tools:
            func.log("DEBUG: Auto-Injecting test tools...", level="DEBUG")
            raw_tools = self.get_test_tools()
            
        tools = self._prepare_vertex_tools(raw_tools)
        current_options = self.config_kwargs.copy()
        
        if options:
            if 'max_tokens' in options:
                current_options['max_output_tokens'] = options['max_tokens']
            if 'temperature' in options:
                current_options['temperature'] = options['temperature']
            if 'top_p' in options:
                current_options['top_p'] = options['top_p']
            if 'top_k' in options:
                current_options['top_k'] = options['top_k']
            # Capture tools if passed in the chat options
            if 'tools' in options:
                tools = options['tools']

        func.debug(f"Gemini Processing {len(history)} messages | Stream: {stream} | Tools attached: {bool(tools)}")
        
        if stream:
            return self._stream_generator(history, dynamic_system_prompt, current_options, tools)
        return self._generate_response_sync(history, dynamic_system_prompt, current_options, tools)

    def _stream_generator(self, history, dynamic_system_prompt, current_options, tools):
        full_content = ""
        first_chunk_received = False
        try:
            from vertexai.generative_models import GenerativeModel
            model = GenerativeModel(self.model_name, system_instruction=[dynamic_system_prompt] if dynamic_system_prompt else None)
            
            responses = model.generate_content(
                history, 
                stream=True, 
                generation_config=self.config_class(**current_options), 
                tools=tools
            )
            
            for r in responses:
                if self.stop_generation_event.is_set(): break
                extracted = self._extract_response_content(r)
                
                if not first_chunk_received:
                    if extracted["type"] == "function_call":
                        func.log(f"{Color.CYAN}[SENTINEL]: ACTION DETECTED -> {extracted['name']}{Color.RESET}")
                        self.trigger("tool_detected", extracted["name"])
                    else:
                        func.log("DEBUG: First chunk is TEXT intent.", level="DEBUG")
                    first_chunk_received = True

                if extracted["type"] == "function_call":
                    yield extracted 
                    return
                    
                if extracted["content"]:
                    full_content += extracted["content"]
                    self.trigger("token", extracted["content"])
                    yield extracted["content"]
        except Exception as e:
            func.error(f"Stream Loop Error: {e}")
            yield f"Error: {e}"
        finally:
            self.trigger(BaseModel.STREAMING_FINISHED_EVENT, full_content)

    def _extract_response_content(self, resp_or_chunk):
        try:
            return {"type": "text", "content": resp_or_chunk.text}
        except Exception:
            if hasattr(resp_or_chunk, 'candidates') and resp_or_chunk.candidates:
                candidate = resp_or_chunk.candidates[0]
                if candidate.content.parts:
                    part = candidate.content.parts[0]
                    if hasattr(part, 'function_call') and part.function_call:
                        fc = part.function_call
                        func.log(f"DEBUG: Extracted Tool Call: {fc.name}", level="DEBUG")
                        return {"type": "function_call", "name": fc.name, "args": dict(fc.args)}
            return {"type": "text", "content": ""}

    def _generate_response_sync(self, history, dynamic_system_prompt, current_options, tools):
        from vertexai.generative_models import GenerativeModel
        model = GenerativeModel(self.model_name, system_instruction=[dynamic_system_prompt] if dynamic_system_prompt else None)
        resp = model.generate_content(history, generation_config=self.config_class(**current_options), tools=tools)
        extracted = self._extract_response_content(resp)
        return extracted if extracted["type"] == "function_call" else extracted["content"]

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