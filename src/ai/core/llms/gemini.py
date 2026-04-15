import os
import threading
import io
import gc
import time
import re
import subprocess
import warnings

# Silencia o aviso de depreciação chato do Vertex AI
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
        self.use_vertex = True
        
        if self.use_vertex:
            if not self._check_gcp_auth():
                func.error("Google Cloud Auth não encontrada!")
                func.out("\n[ ! ] Por favor, corre o seguinte comando no teu terminal:")
                func.out("    gcloud auth application-default login\n")
                raise PermissionError("Autenticação Google Cloud (ADC) necessária para Vertex AI.")
            
            try:
                import vertexai
                from vertexai.generative_models import GenerativeModel, Part, GenerationConfig, Tool
                self.project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT") or "project-02da1a39-478c-49eb-a3e"
                vertexai.init(project=self.project_id, location=location)
                
                self.config_class = GenerationConfig
                self.part_class = Part
                self.tool_class = Tool
                func.log(f"Vertex AI Setup concluído para o modelo {self.model_name}", level="DEBUG")
            except ImportError:
                func.error("Missing 'google-cloud-aiplatform'. Run: pip install google-cloud-aiplatform")
                raise
        else:
            try:
                from google import genai
                from google.genai import types
                self.genai_module = genai
                self.genai_types = types
                
                self.api_key = api_key or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_JARVIS_API_KEY")
                if not self.api_key:
                    raise ValueError("Gemini API Key required for non-vertex mode.")
                self.client = self.genai_module.Client(api_key=self.api_key)
                func.log(f"GenAI SDK Setup concluído para o modelo {self.model_name}", level="DEBUG")
            except ImportError:
                func.error("Missing 'google-genai'. Run: pip install google-genai")
                raise

        model_params = kargs.get('model_params', {}) or {}
        self.config_kwargs = {}
        for param_name, api_name in [
            ('temperature', 'temperature'),
            ('max_new_tokens', 'max_output_tokens'),
            ('top_p', 'top_p'),
            ('top_k', 'top_k')
        ]:
            val = model_params.get(param_name, kargs.get(param_name))
            if val is not None:
                self.config_kwargs[api_name] = val

    def _convert_messages_to_api(self, messages: list):
        if not messages:
            return []
            
        if self.use_vertex:
            from vertexai.generative_models import Content, Part
            return [Content(role="user" if m.get('role', 'user') == "user" else "model", 
                            parts=[Part.from_text(m.get('content', ''))]) 
                    for m in messages if m.get('role') != 'system']
        else:
            return [self.genai_types.Content(
                        role="user" if m.get('role', 'user') == "user" else "model", 
                        parts=[self.genai_types.Part.from_text(text=m.get('content', ''))]
                    ) 
                    for m in messages if m.get('role') != 'system']

    def load_images(self, images: list):
        image_parts = []
        for img in images:
            try:
                import PIL.Image
                img_obj = PIL.Image.open(img) if isinstance(img, str) else img
                img_byte_arr = io.BytesIO()
                img_obj.save(img_byte_arr, format='PNG')
                data = img_byte_arr.getvalue()
                
                if self.use_vertex:
                    image_parts.append(self.part_class.from_data(data=data, mime_type="image/png"))
                else:
                    image_parts.append(self.genai_types.Part.from_bytes(data=data, mime_type="image/png"))
            except Exception as e:
                func.error(f"Image Error: {e}")
        return image_parts

    def _append_images_to_history(self, history, images):
        if not images:
            return
            
        image_parts = self.load_images(images)
        if not image_parts:
            return

        is_last_user = False
        if history:
            is_last_user = getattr(history[-1], 'role', '') == "user"

        if is_last_user:
            if isinstance(history[-1].parts, list):
                history[-1].parts.extend(image_parts)
            else:
                history[-1].parts = list(history[-1].parts) + image_parts
        else:
            if self.use_vertex:
                from vertexai.generative_models import Content
                history.append(Content(role="user", parts=image_parts))
            else:
                history.append(self.genai_types.Content(role="user", parts=image_parts))

    def chat(self, messages: list, images: list = [], stream: bool = True, options: dict = None):
        self.stop_generation_event.clear()
        
        dynamic_system_prompt = self.system_prompt
        for m in messages:
            if m.get('role') == 'system':
                dynamic_system_prompt = m.get('content')
                break
                
        if dynamic_system_prompt:
            dynamic_system_prompt = f"{self.get_system_info()}\n{dynamic_system_prompt}"
            func.log("System Prompt updated with system info!", level="DEBUG")

        history = self._convert_messages_to_api(messages)
        self._append_images_to_history(history, images)

        current_options = self.config_kwargs.copy()
        tools = None
        
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
        else:
            return self._generate_response_sync(history, dynamic_system_prompt, current_options, tools)

    def _log_usage_metadata(self, response_obj, is_stream=False):
        try:
            usage = getattr(response_obj, 'usage_metadata', None)
            if usage:
                in_tokens = getattr(usage, 'prompt_token_count', '?')
                out_tokens = getattr(usage, 'candidates_token_count', '?')
                mode = "Streaming" if is_stream else "Sync Generation"
                func.log(f"{Color.GREEN}{mode} Finished. Tokens -> Input: {in_tokens} | Output: {out_tokens}{Color.RESET}", level="DEBUG")
        except Exception:
            pass

    def _extract_response_content(self, resp_or_chunk):
        """Safely extracts text or function_call from a response chunk/object."""
        try:
            return {"type": "text", "content": resp_or_chunk.text}
        except ValueError:
            # Se falhar o `.text`, verifica se é um function_call
            if hasattr(resp_or_chunk, 'candidates') and resp_or_chunk.candidates and resp_or_chunk.candidates[0].content.parts:
                part = resp_or_chunk.candidates[0].content.parts[0]
                
                # Check for Function Call payload
                if hasattr(part, 'function_call') and part.function_call:
                    func_call = part.function_call
                    # Converter argumentos de forma segura para dicionário Python
                    args_dict = {k: v for k, v in func_call.args.items()} if hasattr(func_call.args, 'items') else dict(func_call.args)
                    return {"type": "function_call", "name": func_call.name, "args": args_dict}
                
                # Fallback para extração manual de texto
                if hasattr(part, 'text'):
                    return {"type": "text", "content": part.text}
                    
            return {"type": "text", "content": ""}

    def _generate_response_sync(self, history, dynamic_system_prompt, current_options, tools):
        if self.use_vertex:
            from vertexai.generative_models import GenerativeModel
            local_model = GenerativeModel(
                model_name=self.model_name,
                system_instruction=[dynamic_system_prompt] if dynamic_system_prompt else None
            )
            
            kwargs = {"generation_config": self.config_class(**current_options)}
            if tools:
                kwargs["tools"] = tools

            resp = local_model.generate_content(history, **kwargs)
            
            extracted = self._extract_response_content(resp)
            self._log_usage_metadata(resp, is_stream=False)
            
            if extracted["type"] == "function_call":
                func.debug(f"Tool Call Triggered: {extracted['name']}")
                return extracted # Return dict so orchestrator handles execution
                
            func.debug(extracted["content"])
            return extracted["content"]

        else:
            if dynamic_system_prompt:
                current_options['system_instruction'] = dynamic_system_prompt
            if tools:
                current_options['tools'] = tools
            
            resp = self.client.models.generate_content(
                model=self.model_name, 
                contents=history, 
                config=self.genai_types.GenerateContentConfig(**current_options)
            )
            
            extracted = self._extract_response_content(resp)
            self._log_usage_metadata(resp, is_stream=False)
            
            if extracted["type"] == "function_call":
                func.debug(f"Tool Call Triggered: {extracted['name']}")
                return extracted 
                
            func.debug(extracted["content"])
            return extracted["content"]

    def _stream_generator(self, history, dynamic_system_prompt, current_options, tools):
        full_response_content = "" 
        last_chunk_with_usage = None
        
        try:
            if self.use_vertex:
                from vertexai.generative_models import GenerativeModel
                local_model = GenerativeModel(
                    model_name=self.model_name,
                    system_instruction=[dynamic_system_prompt] if dynamic_system_prompt else None
                )
                
                kwargs = {
                    "stream": True,
                    "generation_config": self.config_class(**current_options)
                }
                if tools:
                    kwargs["tools"] = tools

                responses = local_model.generate_content(history, **kwargs)
                
                for r in responses:
                    if self.stop_generation_event.is_set(): break
                    
                    extracted = self._extract_response_content(r)
                    
                    if extracted["type"] == "function_call":
                        # Em streaming, function calls vêm inteiras num único chunk normalmente
                        yield extracted 
                        return # Aborta o stream de texto porque a AI quer usar uma tool
                        
                    chunk_text = extracted["content"]
                    if chunk_text:
                        full_response_content += chunk_text
                        self.trigger("token", chunk_text)
                        yield chunk_text
                    
                    if getattr(r, 'usage_metadata', None):
                        last_chunk_with_usage = r

            else:
                if dynamic_system_prompt:
                    current_options['system_instruction'] = dynamic_system_prompt
                if tools:
                    current_options['tools'] = tools
                
                responses = self.client.models.generate_content_stream(
                    model=self.model_name, 
                    contents=history,
                    config=self.genai_types.GenerateContentConfig(**current_options)
                )
                for chunk in responses:
                    if self.stop_generation_event.is_set(): break
                    
                    extracted = self._extract_response_content(chunk)
                    
                    if extracted["type"] == "function_call":
                        yield extracted
                        return
                        
                    chunk_text = extracted["content"]
                    if chunk_text: 
                        full_response_content += chunk_text
                        self.trigger("token", chunk_text)
                        yield chunk_text
                    
                    if getattr(chunk, 'usage_metadata', None):
                        last_chunk_with_usage = chunk
                        
            if last_chunk_with_usage:
                self._log_usage_metadata(last_chunk_with_usage, is_stream=True)
            else:
                func.log(f"{Color.GREEN}Streaming Finished. Output length: {len(full_response_content)} chars{Color.RESET}", level="DEBUG")
                
        except Exception as e:
            func.error(f"Stream Error: {e}")
            self.trigger("token", f"Error: {e}")
            yield f"Error: {e}"
        finally:
            self.trigger(BaseModel.STREAMING_FINISHED_EVENT, full_response_content)

    def is_gpu_available(self): return False
    def clean_cache(self): gc.collect()
    
    def _check_gcp_auth(self):
        adc_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if adc_path and os.path.exists(adc_path):
            return True
            
        if os.name == 'nt': 
            default_path = os.path.join(os.environ.get('APPDATA', ''), 'gcloud', 'application_default_credentials.json')
        else: 
            default_path = os.path.expanduser('~/.config/gcloud/application_default_credentials.json')
            
        if os.path.exists(default_path):
            return True
            
        try:
            result = subprocess.run(["gcloud", "auth", "print-access-token"], 
                                    capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except:
            return False