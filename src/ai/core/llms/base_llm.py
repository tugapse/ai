import os
import gc
import threading
from typing import Callable, Optional, List, Dict, Any
from ai.config import ProgramConfig, ProgramSetting
from ai import functions
from ai.entities.model_enums import InferenceBackend
from ai.tools.tool_registry import ToolRegistry


class TokenCountInfo:
    """Tracks and calculates real-time token tracking metadata for inference context tracking."""

    def __init__(self) -> None:
        self.prompt_count = 0
        self.max_context_window = 0
        self.max_output_tokens = 0
        self.total_prompt_count = 0
        self.printed_tokens_count = 0

    def get_log_string(self) -> str:
        """Calculates context window usage percentages and prints a formatted log metric string."""
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


class ModelParams:
    """Encapsulates execution parameters, generation configurations, and sampler constraints for LLM requests."""

    def __init__(self, **kargs) -> None:
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

    def to_dict(self) -> Dict[str, Any]:
        """Filters out uninitialized parameters and maps configurations to a standard dictionary format."""
        return {k: v for k, v in self.__dict__.items() if v is not None}


class BaseModel:
    """Abstract base class handling state management, context building, and tool interception logic for inference models."""

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
    HIL_TOOLS:list[str]

    def __init__(self, model_name: str, system_prompt: str = "", **kargs) -> None:
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
        self.tool_registry: Optional[ToolRegistry] = kargs.get("tool_registry")
        self.HIL_TOOLS = ProgramConfig.get_current().get(ProgramSetting.HIL_TOOLS)
        
    
    def _load_llm_params(self, **kwargs) -> None:
        self.token_info_count.max_context_window = self.options.get("n_ctx", 2048)
        self.token_info_count.max_output_tokens = self.options.get("max_new_tokens", 2048)


    def handle_sentinel(self, content: str, is_intercepting: bool, sentinel_buffer: str):
        """Monitors and intercepts streaming chunks matching syntax blocks to extract raw agent tool calls."""
        TRIGGER_PREFIXES = ["____", "<|"]
        
        if not is_intercepting:
            if any(p in content for p in TRIGGER_PREFIXES) or \
               any(p in (sentinel_buffer + content) for p in TRIGGER_PREFIXES):
                return None, sentinel_buffer + content, True, False
            
            # Retain a short tail to capture syntax markers split across chunk frames
            new_tail = (sentinel_buffer + content)[-3:]
            return content, new_tail, False, False
        else:
            new_buffer = sentinel_buffer + content
            action = ToolRegistry.parse_manual_tags(new_buffer)
            
            if action:
                return action, "", False, True
            
            return None, new_buffer, True, False

    def init_pytorch_cuda(self) -> None:
        """Validates hardware capabilities and switches execution backend if PyTorch CUDA is present."""
        try:
            import torch

            if torch.cuda.is_available():
                self.inference_device = InferenceBackend.GPU_CUDA
                functions.log("PyTorch CUDA available. Set inference device to GPU.")
            else:
                functions.log("PyTorch CUDA not available. Using CPU.")
        except ImportError:
            functions.log("PyTorch not found. Using CPU.")

    def _prepare_input(self, messages: List[Dict[str, Any]]):
        """Converts conversations into raw string formats or explicit tokens using templates or legacy text logic."""
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

    def add_event(self, event_name: str, listener: Callable) -> None:
        """Registers callback functions to hook into specific model execution lifecycle steps."""
        if event_name not in self.listeners:
            self.listeners[event_name] = []
        self.listeners[event_name].append(listener)

    def trigger(self, event_name: str, data: Any = None) -> None:
        """Executes all registered listener callbacks tied to a specific system event string."""
        if event_name in self.listeners:
            for listener in self.listeners[event_name]:
                listener(data)

    @staticmethod
    def create_message(role: str, content: str) -> Dict[str, str]:
        """Constructs a structured message dictionary mapping role types to text payloads."""
        return {"role": role, "content": content}

    def get_system_info(self) -> str:
        """Fetches host environment specs to pass down real-time OS and time data to system prompts."""
        system_info = functions.get_system_info_prompt_concise()
        current_time_str = system_info.get("time", "Unknown Time")
        os_info = system_info.get("os", "Unknown OS")
        return f"System Context: (Time: {current_time_str} | OS: {os_info})"

    def check_system_prompt(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Ensures system metadata context sits atop history arrays, altering roles to fit prompt setups."""
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

    def clean_cache(self) -> None:
        """Flushes residual memory buffers and invokes garbage collection routines to free hardware VRAM."""
        if self.is_gpu_available():
            try:
                import torch

                torch.cuda.empty_cache()
            except ImportError:
                pass
        gc.collect()

    def is_gpu_available(self) -> bool:
        """Checks if the internal inference state and driver setups permit hardware GPU computing."""
        if self.inference_device == InferenceBackend.GPU_CUDA:
            try:
                import torch

                return torch.cuda.is_available()
            except ImportError:
                return False
        return False

    def request_shutdown(self) -> None:
        """Halts running generation streams, signals execution exit, and cleans local memory allocations."""
        self.stop_generation_event.set()
        self.join_generation_thread(2)
        self.clean_cache()

    def join_generation_thread(self, timeout: float = 0.0) -> None:
        """Blocks execution until the background streaming generation thread fully unwinds or times out."""
        if self._generation_thread and self._generation_thread.is_alive():
            self._generation_thread.join(timeout=timeout)
        self.stop_generation_event.clear()

    def chat(
        self,
        messages: list,
        images: list = [],
        stream: bool = True,
        options: object = {},
    ):
        """Abstract interface endpoint intended to process conversations and deliver textual streams."""
        raise NotImplementedError

    def generate_structured(
        self, messages: list, schema: object, images: list = [], options: object = {}
    ):
        """Abstract interface endpoint intended to force generation streams to follow rigid structural JSON parameters."""
        raise NotImplementedError

    def unload(self) -> None:
        """Abstract interface checkpoint intended to completely purge engine allocations from hardware modules."""
        functions.error("Subclasses must implement unload to clear model resources.")