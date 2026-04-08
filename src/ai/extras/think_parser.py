import functions as func
import re
from extras.thinking_log_manager import ThinkingLogManager

class ThinkingAnimationHandler:
    """
    Handles display and state management for LLM "thinking" tags.
    Refactored for readability while maintaining original logic and behavior.
    """

    SPINNER_CHARS: list = ["|", "/", "-", "\\"]
    PROGRESS_BAR_LENGTH: int = 5
    THINKING_PREFIX: str = "Thinking"
    MAX_UNTILL_THINK_DRAW: int = 3

    THINK_START_PATTERN = re.compile(r"\s*<think>\s*")
    THINK_END_PATTERN = re.compile(r"\s*</think>\s*")
    CONTROL_CHARS_PATTERN = re.compile(r"[\x00-\x09\x0B-\x1F\x7F]")
    PARTIAL_TAG_PATTERN = re.compile(r"<th(?:in(?:k>)?|/th(?:ink>)?|i|n|k|/i|/n|/k)?")

    def __init__(
        self,
        enable_display: bool = True,
        mode: str = "dots",
        log_manager: ThinkingLogManager = None,
        show_animation: bool = False
    ):
        self.enable_display = enable_display
        self.show_animation = show_animation
        self.mode = mode.lower()
        self._log_manager = log_manager

        self._is_thinking_active = False
        self._has_thinking_intro_printed = False
        self._current_thinking_count = 0
        self._token_accumulation_buffer = ""

    def process_token_and_thinking_state(self, raw_token_string: str) -> tuple[bool, str]:
        self._token_accumulation_buffer += raw_token_string
        cleaned_buffer = self.CONTROL_CHARS_PATTERN.sub("", self._token_accumulation_buffer)

        if not self.enable_display:
            display_content = self._token_accumulation_buffer
            self._token_accumulation_buffer = ""
            return self._is_thinking_active, display_content

        # 1. Handle End Tag
        end_match = self.THINK_END_PATTERN.search(cleaned_buffer)
        if end_match:
            if self._is_thinking_active:
                content_after_end_tag = cleaned_buffer[end_match.end() :]
                
                # Clear animation line
                self.print_think(
                    "\r" + (" " * self.get_max_thinking_indicator_length()) + "\r",
                    end="",
                )

                self._is_thinking_active = False
                self._has_thinking_intro_printed = False
                self._current_thinking_count = 0
                self._token_accumulation_buffer = content_after_end_tag.strip()

                return self._is_thinking_active, self._token_accumulation_buffer
            else:
                self._token_accumulation_buffer = self.THINK_END_PATTERN.sub("", cleaned_buffer)

        # 2. Handle Start Tag
        start_match = self.THINK_START_PATTERN.search(self._token_accumulation_buffer)
        if start_match:
            if not self._is_thinking_active:
                token_content_for_display = self._token_accumulation_buffer[: start_match.start()]

                self._is_thinking_active = True
                self._current_thinking_count = 0

                if self._log_manager and not self._has_thinking_intro_printed:
                    self._log_manager.write_session_header()

                if not self._has_thinking_intro_printed:
                    self.print_think(self.THINKING_PREFIX, end="", flush=True)
                    self._has_thinking_intro_printed = True

                self._token_accumulation_buffer = self._token_accumulation_buffer[start_match.end() :]
                return self._is_thinking_active, token_content_for_display
            else:
                self._token_accumulation_buffer = self.THINK_START_PATTERN.sub("", self._token_accumulation_buffer)

        # 3. Handle Active Thinking State
        if self._is_thinking_active:
            self._current_thinking_count += 1
            if self._log_manager:
                self._log_manager.write_thinking_log(raw_token_string)
            
            self._draw_animation_frame()
            return self._is_thinking_active, ""

        # 4. Normal Output or Partial Tag handling
        if not self.PARTIAL_TAG_PATTERN.search(cleaned_buffer):
            token_content_for_display = self._token_accumulation_buffer
            self._token_accumulation_buffer = ""
            return self._is_thinking_active, token_content_for_display
        else:
            return self._is_thinking_active, raw_token_string

    def _draw_animation_frame(self):
            """Helper to handle specific animation drawing modes."""
            # ANSI escape code to clear the entire line
            clear_line = "\033[2K"

            if self.mode == "dots":
                self.print_think(".", end="", flush=True)

            elif self.mode == "spinner":
                idx = (self._current_thinking_count // self.MAX_UNTILL_THINK_DRAW) % len(self.SPINNER_CHARS)
                char = self.SPINNER_CHARS[idx]
                # Clear line, return to start, then print
                self.print_think(f"\r{clear_line}{self.THINKING_PREFIX}... {char}", end="", flush=True)

            elif self.mode == "progressbar":
                pos = ((self._current_thinking_count // self.MAX_UNTILL_THINK_DRAW) - 1) % self.PROGRESS_BAR_LENGTH
                bar = ["-"] * self.PROGRESS_BAR_LENGTH
                bar[pos] = "#"
                bar_str = "".join(bar)
                # Clear line, return to start, then print
                self.print_think(f"\r{clear_line}{self.THINKING_PREFIX}... [{bar_str}]", end="", flush=True)

    def get_max_thinking_indicator_length(self):
        return len(self.THINKING_PREFIX + "... [" + "-" * self.PROGRESS_BAR_LENGTH + "]") + 1
        
    def print_think(self, message, **kargs):
        if self.show_animation: 
            func.out(message, **kargs)