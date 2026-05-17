import re
import unicodedata
from typing import Optional, Any, Callable, List
from dataclasses import dataclass, field
import functions as func

# We keep the SpeechBridge as it handles the "Sir, I've put the code on screen" logic
from modules.voice.speech_bridge import SpeechBridge
from extras.output_printer import OutputPrinter 

@dataclass
class StreamResult:
    accumulated_text: str
    interrupted: bool = False
    tool_calls: List[Any] = field(default_factory=list) # Track calls for logic execution

class StreamOrchestrator:
    def __init__(
        self, 
        voice_module: Any, 
        output_printer: OutputPrinter, 
        handler_manager: Any, 
        token_processor: Any,
        debug_voice: bool = False,
        on_tool_call: Optional[Callable[[Any], None]] = None
    ):
        self.printer = output_printer
        self.handler = handler_manager
        self.processor = token_processor
        self.speech_bridge = SpeechBridge(voice_module, debug=debug_voice)
        self.on_tool_call = on_tool_call

        self.accumulated_text = ""
        self.tool_calls = []
        self.started_response = False

    def _sanitize(self, token: str) -> str:
        sanitized = unicodedata.normalize('NFKC', token)
        sanitized = re.sub(r'[^\x20-\x7E\n\t]', '', sanitized)
        return sanitized

    def run(self, stream_generator) -> StreamResult:
        self.tool_calls = []
        self.accumulated_text = "" # Reset for the new turn
        try:
            for raw_token in stream_generator:
                # 1. Handle Dictionary Tokens (Native Tool Calls)
                if isinstance(raw_token, dict):
                    self.tool_calls.append(raw_token)
                    # We MUST populate accumulated_text so the conversation history
                    # isn't empty, preventing the 400 InvalidArgument error.
                    self.accumulated_text += str(raw_token) 
                    if self.on_tool_call:
                        self.on_tool_call(raw_token)
                    continue 

                # 2. String Sanitization
                token = self._sanitize(raw_token)
                if not token:
                    continue

                processed_token = self.printer.process_token(token)
                if processed_token is None:
                    continue

                display_to_user, content, is_tool_call = self.handler.process_token_chain(processed_token)

                # 3. Handle Silent Tool Triggers vs UI Content
                if is_tool_call:
                    self.tool_calls.append(content)
                    # We accumulate the content so history stays valid, 
                    # but we DON'T call _display_and_relay so it stays off-screen.
                    self.accumulated_text += content 
                    if self.on_tool_call:
                        self.on_tool_call(content)
                elif display_to_user:
                    # This method handles both accumulation AND display/voice
                    self._display_and_relay(content)

            # Drain any remaining buffers
            if hasattr(self.printer, 'flush'):
                final_chunk = self.printer.flush()
                if final_chunk:
                    display_to_user, content, is_tool_call = self.handler.process_token_chain(final_chunk)
                    
                    if is_tool_call:
                        self.tool_calls.append(content)
                        self.accumulated_text += content
                        if self.on_tool_call:
                            self.on_tool_call(content)
                    elif display_to_user:
                        self._display_and_relay(content)

            self.speech_bridge.flush()

            return StreamResult(
                accumulated_text=self.accumulated_text,
                tool_calls=self.tool_calls
            )

        except KeyboardInterrupt:
            self.speech_bridge.abort()
            return StreamResult(
                accumulated_text=self.accumulated_text, 
                interrupted=True,
                tool_calls=self.tool_calls
            )
        except Exception as e:
            self.speech_bridge.flush()
            raise e

    def _display_and_relay(self, content: str):
        if not self.started_response:
            self.started_response = True
        
        formatted = self.processor.process_token(content)
        self.accumulated_text += content
        func.out(formatted, end="", flush=True)
        self.speech_bridge.feed(content)