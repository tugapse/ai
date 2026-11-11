import os
import io
import gc
import subprocess
import warnings
import json

# Suppress legacy deprecation warnings
warnings.filterwarnings(
    "ignore", 
    message=".*This feature is deprecated as of June 24, 2025.*", 
    category=UserWarning
)

from google import genai
from google.genai import types

import ai.functions as func
from ai.core.llms.base_llm import BaseModel, ModelParams 
from ai.core.llms.api_retry import LLMAPIError, RetryPolicy, call_with_retry, stream_with_retry, wrap_error
from ai.color import Color
from ai.tools.tool_registry import ToolRegistry


class GeminiAPIModel(BaseModel):
    """
    Implements the Gemini API model interface, supporting both direct API key usage 
    and Google Vertex AI integration.

    This class handles the configuration, message conversion, and execution of 
    chat and generation requests against the Gemini models.
    """
    def __init__(self, model_name="gemini-2.5-flash", system_prompt="", api_key=None, use_vertex=False, project_id=None, location="global", **kargs):
        func.log(f"Initializing GeminiAPIModel for model: {model_name}")
        super().__init__(model_name, system_prompt, **kargs)
        
        self.use_vertex = use_vertex
        self.project_id = project_id or os.environ.get("GOOGLE_CLOUD_PROJECT")
        self.location = location

        # Timeouts/retries: "timeout", "connect_timeout", "max_retries", "retry_max_wait" in model_properties.
        self.retry_policy = RetryPolicy.from_config(kargs, kargs.get('model_params') or {})
        # google-genai expects milliseconds; httpx applies it per operation (connect/read), not to the whole stream.
        http_options = types.HttpOptions(timeout=int(self.retry_policy.timeout * 1000))

        if self.use_vertex:
            if not self._check_gcp_auth():
                func.error("Google Cloud Auth not found!")
                raise PermissionError("Google Cloud authentication (ADC) required.")
            
            self.client = genai.Client(
                vertexai=True,
                project=self.project_id,
                location=self.location,
                http_options=http_options,
            )
            func.log(f"Vertex AI Client ready for {self.model_name}", level="DEBUG")
        else:
            resolved_key = api_key or os.environ.get("GEMINI_API_KEY")
            if not resolved_key:
                func.error("GEMINI_API_KEY not found!")
                raise ValueError("API key required for direct Gemini mode.")
            
            self.client = genai.Client(api_key=resolved_key, http_options=http_options)
            func.log(f"Gemini Developer API Client ready for {self.model_name}", level="DEBUG")

        model_params = kargs.get('model_params', {}) or {}
        self.config_kwargs = {}
        self.token_info_count.max_context_window = model_params.get('n_ctx', self.CONTEXT_WINDOW_1M)

        param_map = [
            ('temperature', 'temperature'),
            ('max_new_tokens', 'max_output_tokens'),
            ('top_p', 'top_p'),
            ('top_k', 'top_k')
        ]
        for param, api_param in param_map:
            val = model_params.get(param, kargs.get(param))
            if val is not None:
                self.config_kwargs[api_param] = val

    def _convert_messages_to_api(self, messages: list) -> list:
        """
        Converts the internal message format into the format required by the Google GenAI API,
        remaining completely agnostic to the upper-layer prompting protocol.
        """
        if not messages:
            return []

        api_messages = []
        for m in messages:
            role = m.get('role')
            if role == 'system':
                continue

            parts_to_add = []
            v_role = "user" if role in ['user', 'tool', 'function'] else "model"

            if role in ['tool', 'function']:
                text = f"[SYSTEM RESULT FOR TOOL '{m.get('name', 'unknown')}']\n{m.get('content')}"
                parts_to_add.append(text)
            else:
                if m.get('content'):
                    parts_to_add.append(str(m.get('content')))
                
                if role in ['assistant', 'model'] and m.get('tool_calls'):
                    for call in m['tool_calls']:
                        name = call['function']['name']
                        args = call['function']['arguments']
                        args_str = json.dumps(args) if isinstance(args, dict) else args
                        parts_to_add.append(f"____@tool call:{name}{args_str}")

            if not parts_to_add:
                continue

            combined_text = "\n".join(parts_to_add)

            if api_messages and api_messages[-1].role == v_role:
                prev_text = api_messages[-1].parts[0].text
                api_messages[-1].parts[0] = types.Part.from_text(text=f"{prev_text}\n\n{combined_text}")
            else:
                api_messages.append(types.Content(role=v_role, parts=[types.Part.from_text(text=combined_text)]))
            
        return api_messages

    def chat(self, messages: list, images: list = [], stream: bool = True, options: dict = None):
        self.stop_generation_event.clear()
        
        # 1. Garantir que o self.system_prompt NUNCA é descartado
        system_parts = [str(self.get_system_info())]
        if self.system_prompt:
            system_parts.append(str(self.system_prompt))
            
        for m in messages:
            if m.get('role') == 'system' and m.get('content'):
                content_str = str(m.get('content'))
                if content_str not in system_parts:
                    system_parts.append(content_str)
            
        dynamic_system_prompt = "\n\n".join(system_parts)

        # DEBUG CRÍTICO: Verificar se as regras de XML estão mesmo presentes no prompt!
        has_xml_rules = "<response>" in dynamic_system_prompt
        func.log(f"[GEMINI DEBUG] System Prompt Length: {len(dynamic_system_prompt)} chars | Has <response> tag: {has_xml_rules}", level="DEBUG")

        contents = self._convert_messages_to_api(messages)
        self._append_images_to_history(contents, images)

        current_options = self.config_kwargs.copy()
        if options:
            if 'max_tokens' in options: current_options['max_output_tokens'] = options['max_tokens']
            if 'temperature' in options: current_options['temperature'] = options['temperature']
            if 'top_p' in options: current_options['top_p'] = options['top_p']
            if 'top_k' in options: current_options['top_k'] = options['top_k']

        if dynamic_system_prompt:
            current_options['system_instruction'] = dynamic_system_prompt

        config = types.GenerateContentConfig(**current_options)

        func.debug(f"Gemini ({'Vertex' if self.use_vertex else 'Direct'}) processing {len(contents)} messages | Stream: {stream}")
        
        if stream:
            return self._stream_generator(contents, config)
        return self._generate_response_sync(contents, config)

    def _stream_generator(self, contents, config):
        full_content = ""
        sentinel_buffer = ""
        is_intercepting = False
        finish_reason = None
        block_reason = None

        try:
            response_stream = stream_with_retry(
                lambda: self.client.models.generate_content_stream(
                    model=self.model_name,
                    contents=contents,
                    config=config
                ),
                self.retry_policy, "Gemini", self.stop_generation_event,
            )

            for chunk in response_stream:
                if self.stop_generation_event.is_set():
                    break

                candidates = getattr(chunk, "candidates", None) or []
                if candidates and getattr(candidates[0], "finish_reason", None):
                    finish_reason = candidates[0].finish_reason
                feedback = getattr(chunk, "prompt_feedback", None)
                if feedback is not None and getattr(feedback, "block_reason", None):
                    block_reason = feedback.block_reason

                content = chunk.text or ""
                if not content:
                    continue
                
                full_content += content
                
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

            if not full_content and not self.stop_generation_event.is_set():
                func.log(f"[Gemini] Empty response (finish_reason={finish_reason}, block_reason={block_reason}).", level="WARN")

        except LLMAPIError as e:
            # Never yield errors as if the model had written them: raise a typed error.
            func.error(f"[Gemini] {e.user_message()}")
            raise
        except Exception as e:
            err = wrap_error(e, "Gemini", attempts=1, partial=bool(full_content))
            func.error(f"[Gemini] {err.user_message()}")
            raise err from e
        finally:
            self.trigger(BaseModel.STREAMING_FINISHED_EVENT, full_content)

    def _generate_response_sync(self, contents, config):
        resp = call_with_retry(
            lambda: self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config
            ),
            self.retry_policy, "Gemini", self.stop_generation_event,
        )
        text = resp.text or ""
        action = ToolRegistry.parse_manual_tags(text)
        return action if action else text

    def _check_gcp_auth(self) -> bool:
        if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            return True
        paths = [
            os.path.expanduser('~/.config/gcloud/application_default_credentials.json'),
            os.path.join(os.environ.get('APPDATA', ''), 'gcloud', 'application_default_credentials.json') if os.name == 'nt' else ''
        ]
        if any(os.path.exists(p) for p in paths if p):
            return True
        try:
            return subprocess.run(["gcloud", "auth", "print-access-token"], capture_output=True, timeout=5).returncode == 0
        except Exception:
            return False

    def load_images(self, images: list) -> list:
        image_parts = []
        for img in images:
            try:
                import PIL.Image
                img_obj = PIL.Image.open(img) if isinstance(img, str) else img
                img_byte_arr = io.BytesIO()
                img_obj.save(img_byte_arr, format='PNG')
                image_parts.append(types.Part.from_bytes(data=img_byte_arr.getvalue(), mime_type="image/png"))
            except Exception as e:
                func.error(f"Image Error: {e}")
        return image_parts

    def _append_images_to_history(self, contents, images):
        if not images or not contents:
            return
        image_parts = self.load_images(images)
        for content in reversed(contents):
            if content.role == "user":
                content.parts.extend(image_parts)
                break

    def is_gpu_available(self) -> bool:
        return False

    def clean_cache(self):
        gc.collect()