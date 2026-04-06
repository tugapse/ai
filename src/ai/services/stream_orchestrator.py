import re
import unicodedata
from typing import Optional, Any
from dataclasses import dataclass

from entities.model_enums import EngineType
from color import Color, format_text
import functions as func

@dataclass
class StreamResult:
    """Encapsulates the outcome of an LLM stream for the main Program."""
    accumulated_text: str
    tool_call_detected: bool
    tool_buffer: str
    interrupted: bool = False

class StreamOrchestrator:
    """
    Handles the complexity of the LLM token stream:
    - Sanitization & Normalization
    - Tool-tag state management (Normal vs. Tool Capture)
    - Relay to Voice Engine (via process_token)
    - Formatting and Console output
    """

    STATE_NORMAL = "normal"
    STATE_TOOL_CAPTURE = "tool_capture"

    def __init__(
        self, 
        voice_module: Any, 
        output_printer: Any, 
        handler_manager: Any, 
        token_processor: Any,
        assistant_prompt: str = "Assistant: "
    ):
        self.voice = voice_module
        self.printer = output_printer
        self.handler = handler_manager
        self.processor = token_processor
        self.assistant_prompt = assistant_prompt

        self.state = self.STATE_NORMAL
        self.accumulated_text = ""
        self.tool_buffer = ""
        self.is_first_token = True
        self.started_response = False

        # New state for voice buffering
        self.voice_buffer = ""
        self.is_muted = False
        self.sentence_delimiters = re.compile(r'[.?!\n]')

    def _flush_voice_buffer(self):
        """Sends the buffered text to the voice module and clears the buffer."""
        if self.voice and self.voice_buffer.strip():
            # We send a copy and immediately clear, making it more thread-safe
            text_to_speak = self.voice_buffer
            self.voice_buffer = ""
            self.voice.process_token(text_to_speak)


    def _sanitize(self, token: str) -> str:
        """Cleans and normalizes tokens for consistent processing."""
        # Normalize Unicode (NFKC)
        sanitized = unicodedata.normalize('NFKC', token)
        # Remove non-printable characters except newlines and tabs
        sanitized = re.sub(r'[^\x20-\x7E\n\t]', '', sanitized)
        return sanitized

    def run(self, stream_generator) -> StreamResult:
        """
        Processes the LLM generator tokens until completion or interruption.
        Returns a StreamResult containing the text or tool data.
        """
        try:
            for raw_token in stream_generator:
                token = self._sanitize(raw_token)
                if not token:
                    continue

                # 1. Identify Tool Initiation
                if self.is_first_token:
                    self.is_first_token = False
                    if token.strip().startswith("<tool>"):
                        self.state = self.STATE_TOOL_CAPTURE
                
                # 2. Branch logic based on current state
                if self.state == self.STATE_TOOL_CAPTURE:
                    # TOOL MODE: Collect tokens until closing tag
                    self.tool_buffer += token
                    if "</tool>" in self.tool_buffer:
                        return StreamResult(
                            accumulated_text="", 
                            tool_call_detected=True, 
                            tool_buffer=self.tool_buffer
                        )
                    continue

                # NORMAL MODE: Handle Printing/Thinking/Voice
                # Use OutputPrinter to buffer/chunk tokens
                processed_token = self.printer.process_token(token)
                if processed_token is None:
                    continue

                # Use HandlerManager to manage Thinking blocks and UI display
                display_to_user, content, _ = self.handler.process_token_chain(processed_token)

                if display_to_user:
                    self._display_and_relay(content)

            # Natural completion of stream
            return StreamResult(
                accumulated_text=self.accumulated_text,
                tool_call_detected=False,
                tool_buffer=""
            )

        except KeyboardInterrupt:
            # Trap the interrupt: Stop voice immediately
            if self.voice:
                self.voice.abort()
            
            # Return partial text so history is preserved
            return StreamResult(
                accumulated_text=self.accumulated_text,
                tool_call_detected=False,
                tool_buffer="",
                interrupted=True
            )

    def _display_and_relay(self, content: str):
        """Internal helper to manage dual output: Voice and Console."""
        if not self.started_response:
            # Print the header (e.g., "Assistant: ") if this is the first visible content
            func.out(format_text(self.assistant_prompt, Color.PURPLE) + Color.RESET, end="")
            self.started_response = True
        
        # A. Relay to Voice Module (Async background work)
        if self.voice:
            self.voice.process_token(content)

        # B. Format for Console and store for history
        formatted = self.processor.process_token(content)
        self.accumulated_text += content
        func.out(formatted, end="")