import os
import gc
import threading
import json
import re
from typing import Callable, Optional
import functions
from entities.model_enums import InferenceBackend
from tools.tool_registry import ToolRegistry


class TokenCountInfo:
    def __init__(self) -> None:
        self.prompt_count = 0
        self.max_context_window = 0
        self.max_output_tokens = 0
        self.total_prompt_count = 0
        self.printed_tokens_count = 0

    def get_log_string(self) -> str:
        """Returns a condensed 'fuel gauge' of the current token state."""
        usage = (
            (
                self.total_prompt_count
                / (self.max_context_window - self.max_output_tokens)
                * 100
            )
            if self.max_context_window > 0
            else 0
        )
        return (
            f"Tokens: [P: {self.prompt_count} | T: {self.total_prompt_count} | Out: {self.printed_tokens_count}] "
            f"Window: {self.max_context_window-self.max_output_tokens} ({usage:.1f}%)"
        )


class BaseModel:
    CONTEXT_WINDOW_SMALL = 2048
    CONTEXT_WINDOW_MEDIUM = 4096
    CONTEXT_WINDOW_LARGE = 8192
    CONTEXT_WINDOW_XLARGE = 16384
    CONTEXT_WINDOW_HUGE = 32768
    CONTEXT_WINDOW_GIANT = 65536
    CONTEXT_WINDOW_128K = 128748
    CONTEXT_WINDOW_256K = 262144
    CONTEXT_WINDOW_1M = 1048576
    CONTEXT_WINDOW_2M = 2097152

    STREAMING_FINISHED_EVENT = "streaming_finished"

    # --- HUMAN-IN-THE-LOOP (HIL) GATEKEEPER ---
    # Tools that require manual user confirmation before execution.
    HIL_TOOLS = ["execute_command", "write_file", "patch_file", "delete_file"]

    def __init__(self, model_name, system_prompt=None, **kargs):
        self.model_name = model_name
        self.system_prompt = system_prompt
        self.listeners = {}
        self.options = {}
        self.tokenizer = None
        self.override_system_by_user_template = kargs.get(
            "override_system_by_user_template", False
        )

        self.stop_generation_event = threading.Event()
        self._generation_thread = None
        self.inference_device = InferenceBackend.CPU
        self.token_info_count = TokenCountInfo()

        # Registry instance to be injected by the Orchestrator
        self.tool_registry: Optional[ToolRegistry] = kargs.get("tool_registry")

    # =========================================================================
    # J.A.R.V.I.S. PROTOCOL & TOOL SCHEMATICS
    # =========================================================================

    def _parse_docstring_to_schema(self, func_name: str, func_ref: Callable) -> dict:
        """
        Dynamically translates Python docstrings into an LLM-friendly JSON Schema.
        Enforces a mandatory 'intent' property for latent reasoning.
        """
        doc = func_ref.__doc__ or "No description provided."
        lines = doc.strip().split("\n")

        description = ""
        properties = {
            "intent": {
                "type": "string",
                "description": "Clear reasoning of why this tool is being called and the expected outcome.",
            }
        }
        required = ["intent"]

        state = "desc"
        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith("Args:"):
                state = "args"
                continue
            elif line.startswith("Returns:"):
                state = "returns"
                continue

            if state == "desc":
                description += line + " "
            elif state == "args":
                # Matches: param_name (type): description
                match = re.match(r"^(\w+)\s*\(([^)]+)\)\s*:\s*(.*)$", line)
                if match:
                    p_name, p_type, p_desc = match.groups()

                    json_type = "string"
                    if "int" in p_type.lower():
                        json_type = "integer"
                    elif "bool" in p_type.lower():
                        json_type = "boolean"
                    elif "list" in p_type.lower():
                        json_type = "array"

                    properties[p_name] = {
                        "type": json_type,
                        "description": p_desc.strip(),
                    }

                    if "optional" not in p_type.lower():
                        required.append(p_name)

        return {
            "name": func_name,
            "description": description.strip(),
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }

    def format_tools_for_prompt(self) -> str:
        """
        Constructs the system access manual using a generic protocol.
        """
        if not self.tool_registry:
            return ""

        all_tools = self.tool_registry.get_all_tools()
        if not all_tools:
            return ""

        manual = "\n\n[PROTOCOL: SYSTEM ACCESS]\n"
        for name, ref in all_tools.items():
            schema = self._parse_docstring_to_schema(name, ref)
            manual += f"Function: {schema['name']} | Desc: {schema['description']} | Schema: {json.dumps(schema['parameters'])}\n"

        manual += (
            "\n[CRITICAL RULE: TOOL CALLING]\n"
            "1. You have NO direct access to the environment or system state unless you use a tool.\n"
            '2. To use a tool, you MUST output: ____@tool call:name{"intent":"your reasoning", "args":{...}}\n'
            "3. DO NOT use XML tags or alternate markers. Only ____@tool is valid.\n"
            "4. Stop writing immediately after the tool call closing brace.\n"
            "5. Only call ONE tool per response turn.\n"
        )
        return manual

    def format_tools_for_prompt(self) -> str:
        """
        Constructs the system access manual using a generic protocol.
        Safely handles missing keys for legacy or hardcoded tool schemas.
        """
        if not self.tool_registry:
            return ""
            
        all_tools = self.tool_registry.get_all_tools()
        if not all_tools:
            return ""

        manual = "\n\n[PROTOCOL: SYSTEM ACCESS]\n"
        for name, ref in all_tools.items():
            # If ref is a callable, parse it. If it's already a dict, use it directly.
            schema = self._parse_docstring_to_schema(name, ref) if callable(ref) else ref
            
            # Use .get() to safely handle missing 'returns' or 'description' keys
            f_name = schema.get('name', name)
            f_desc = schema.get('description', 'No description provided.')
            f_returns = schema.get('returns', 'Standard status dictionary.')
            f_params = json.dumps(schema.get('parameters', {}))
            
            manual += f"Function: {f_name} | Desc: {f_desc} | Returns: {f_returns} | Schema: {f_params}\n"
        
        manual += (
            "\n[CRITICAL RULE: TOOL CALLING]\n"
            "1. You have NO direct access to the environment or system state unless you use a tool.\n"
            "2. To use a tool, you MUST output: ____@tool call:name{\"intent\":\"your reasoning\", \"param_name\":\"value\"}\n"
            "3. DO NOT use XML tags or alternate markers. Only ____@tool is valid.\n"
            "4. Stop writing immediately after the tool call closing brace.\n"
            "5. Only call ONE tool per response turn.\n"
        )
        return manual

    def parse_manual_tags(self, text: str):
        """Standardized regex parser for catching tool triggers in the stream."""
        
        # Matches J.A.R.V.I.S. tags AND Gemma's <|tool_call> artifacts
        pattern = r"(?:____@tool|____@|<\|?tool_call\|?>)\s*(?:call:)?(\w+)\s*(\{.*?\})"
        match = re.search(pattern, text, re.DOTALL)
        
        if match:
            name, raw_args = match.group(1), match.group(2)
            
            # 1. Clean Gemma's weird quote artifacts
            clean_args = raw_args.replace('<|"|>', '"').replace('<|"', '"').replace('"|>', '"')
            
            # 2. Fix unquoted JSON keys (e.g., {content: "..."} -> {"content": "..."})
            clean_args = re.sub(r'([{,]\s*)([a-zA-Z0-9_]+)\s*:', r'\1"\2":', clean_args)
            
            try:
                # 3. Use strict=False to forgive literal newlines inside strings
                parsed_args = json.loads(clean_args, strict=False)
                
                # Pop the 'intent' key so it doesn't crash Python functions
                if isinstance(parsed_args, dict) and "intent" in parsed_args:
                    del parsed_args["intent"]
                    
                return {"type": "function_call", "name": name, "args": parsed_args}
            except Exception as e:
                import functions as func
                func.log(f"DEBUG: JSON parse fallback triggered for {name}. Error: {e}", level="DEBUG")
                return {"type": "function_call", "name": name, "args": {"raw": raw_args}}
                
        return None
    
    def handle_sentinel(self, content: str, is_intercepting: bool, sentinel_buffer: str):
        """
        Unified Sentinel logic. Removed hard character cap to allow 
        large tool payloads (like write_file/patch_file).
        """
        TRIGGER_PREFIXES = ["____", "<|"]
        
        if not is_intercepting:
            # Check if this chunk or the potential transition triggers interception
            if any(p in content for p in TRIGGER_PREFIXES) or \
               any(p in (sentinel_buffer + content) for p in TRIGGER_PREFIXES):
                return None, sentinel_buffer + content, True, False
            
            # Not intercepting: pass through content, but keep a tiny tail for prefix detection
            new_tail = (sentinel_buffer + content)[-3:]
            return content, new_tail, False, False
        else:
            # Currently intercepting: buffer everything and try to parse
            new_buffer = sentinel_buffer + content
            action = self.parse_manual_tags(new_buffer)
            
            if action:
                # Tool found! Stop stream and return the action dictionary
                return action, "", False, True
            
            # Hard cap removed. We rely on the model eventually closing the JSON 
            # or the StreamOrchestrator timeout/interruption.
            return None, new_buffer, True, False

    # =========================================================================
    # CORE SYSTEM UTILITIES
    # =========================================================================

    def init_pytorch_cuda(self):
        try:
            import torch

            if torch.cuda.is_available():
                self.inference_device = InferenceBackend.GPU_CUDA
                functions.log("PyTorch CUDA available. Set inference device to GPU.")
            else:
                functions.log("PyTorch CUDA not available. Using CPU.")
        except ImportError:
            functions.log("PyTorch not found. Using CPU.")

    def _prepare_input(self, messages: list):
        
        if not self.tokenizer:
            raise ValueError("Tokenizer we not defined")
        
        if self.system_prompt and not any(m["role"] == "system" for m in messages):
            messages.insert(0, BaseModel.create_message("system", self.system_prompt))

        if (
            hasattr(self.tokenizer, "apply_chat_template")
            and self.tokenizer.apply_chat_template
        ):
            input_string = self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            return self.tokenizer(input_string, return_tensors="pt")
        else:
            input_text = ""
            for msg in messages:
                role = msg.get("role", "user").capitalize()
                input_text += f"{role}: {msg.get('content', '')}\n"
            input_text += "Assistant:"
            return self.tokenizer(input_text, return_tensors="pt")

    def add_event(self, event_name, listener):
        if event_name not in self.listeners:
            self.listeners[event_name] = []
        self.listeners[event_name].append(listener)

    def trigger(self, event_name, data=None):
        if event_name in self.listeners:
            for listener in self.listeners[event_name]:
                listener(data)

    @staticmethod
    def create_message(role: str, content: str) -> dict:
        return {"role": role, "content": content}

    def get_system_info(self) -> str:
        system_info = functions.get_system_info_prompt_concise()
        current_time_str = system_info.get("time", "Unknown Time")
        os_info = system_info.get("os", "Unknown OS")
        return f"System Context: (Time: {current_time_str} | OS: {os_info})"

    def check_system_prompt(self, messages: list):
        enriched_info = self.get_system_info()
        final_content = enriched_info
        if self.system_prompt:
            final_content += f"\n{self.system_prompt}"

        filtered = [
            msg
            for msg in messages
            if not (msg["role"] == "system" or msg.get("original_role") == "system")
        ]
        updated = [BaseModel.create_message("system", final_content)] + filtered

        if self.override_system_by_user_template:
            for msg in updated:
                if msg["role"] == "system":
                    msg["role"] = "user"
                    msg["original_role"] = "system"

        return updated

    def clean_cache(self):
        if self.is_gpu_available():
            try:
                import torch

                torch.cuda.empty_cache()
            except ImportError:
                pass
        gc.collect()

    def is_gpu_available(self):
        if self.inference_device == InferenceBackend.GPU_CUDA:
            try:
                import torch

                return torch.cuda.is_available()
            except ImportError:
                return False
        return False

    def request_shutdown(self):
        self.stop_generation_event.set()
        self.join_generation_thread(2)
        self.clean_cache()

    def join_generation_thread(self, timeout: float = 0.0):
        if self._generation_thread and self._generation_thread.is_alive():
            self._generation_thread.join(timeout=timeout)
        self.stop_generation_event.clear()

    # --- ABSTRACT INTERFACES ---
    def chat(
        self,
        messages: list,
        images: list = [],
        stream: bool = True,
        options: object = {},
    ):
        raise NotImplementedError

    def generate_structured(
        self, messages: list, schema: object, images: list = [], options: object = {}
    ):
        raise NotImplementedError

    def unload(self):
        functions.error("Subclasses must implement unload to clear model resources.")


class ModelParams:
    def __init__(self, **kargs):
        self.num_ctx = kargs.get("num_ctx") or BaseModel.CONTEXT_WINDOW_LARGE
        self.max_new_tokens = kargs.get("max_new_tokens", 2048)
        self.max_length = kargs.get("max_length", 4096)
        self.do_sample = kargs.get("do_sample", True)
        self.top_k = kargs.get("top_k", 50)
        self.top_p = kargs.get("top_p", 0.95)
        self.temperature = kargs.get("temperature", 0.5)
        self.quantization_bits = kargs.get("quantization_bits", 0)
        self.enable_thinking = kargs.get("enable_thinking", True)
        self.presence_penalty = kargs.get("presence_penalty", 1.0)
        self.frequency_penalty = kargs.get("frequency_penalty", 1.0)
        self.use_system_prompt = kargs.get("use_system_prompt", True)
        self.format = kargs.get("format", None)

    def to_dict(self):
        d = {k: v for k, v in self.__dict__.items() if v is not None}
        return d
