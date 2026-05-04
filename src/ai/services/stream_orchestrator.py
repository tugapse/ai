import re
import unicodedata
from typing import Optional, Any
from dataclasses import dataclass
from color import Color, format_text
import functions as func

# We keep the SpeechBridge as it handles the "Sir, I've put the code on screen" logic
from modules.voice.speech_bridge import SpeechBridge
from src.ai.extras.output_printer import OutputPrinter 

@dataclass
class StreamResult:
    accumulated_text: str
    interrupted: bool = False

class StreamOrchestrator:
    def __init__(
        self, 
        voice_module: Any, 
        output_printer: OutputPrinter, 
        handler_manager: Any, 
        token_processor: Any,
        debug_voice: bool = False
    ):
        self.printer = output_printer
        self.handler = handler_manager
        self.processor = token_processor
        self.speech_bridge = SpeechBridge(voice_module, debug=debug_voice)

        self.accumulated_text = ""
        self.started_response = False

    def _sanitize(self, token: str) -> str:
        sanitized = unicodedata.normalize('NFKC', token)
        sanitized = re.sub(r'[^\x20-\x7E\n\t]', '', sanitized)
        return sanitized

    def run(self, stream_generator) -> StreamResult:
        try:
            for raw_token in stream_generator:
                token = self._sanitize(raw_token)
                if not token:
                    continue

                # Process for UI display
                processed_token = self.printer.process_token(token)
                if processed_token is None:
                    continue

                display_to_user, content, _ = self.handler.process_token_chain(processed_token)

                if display_to_user:
                    self._display_and_relay(content)

            # Drain any remaining buffers
            if hasattr(self.printer, 'flush'):
                final_chunk = self.printer.flush()
                if final_chunk:
                    display_to_user, content, _ = self.handler.process_token_chain(final_chunk)
                    if display_to_user:
                        self._display_and_relay(content)

            self.speech_bridge.flush()

            return StreamResult(accumulated_text=self.accumulated_text)

        except KeyboardInterrupt:
            self.speech_bridge.abort()
            return StreamResult(accumulated_text=self.accumulated_text, interrupted=True)
        except Exception as e:
            self.speech_bridge.flush()
            raise e

    def _display_and_relay(self, content: str):
        if not self.started_response:
            self.started_response = True
        
        formatted = self.processor.process_token(content)
        self.accumulated_text += content
        func.out(formatted, end="", flush=True)
        
        # This keeps the "Voice Fixes" (skipping code blocks, announcement variations)
        self.speech_bridge.feed(content)