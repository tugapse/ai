import functions as func
from color import Color
import re

from .thinking_log_manager import ThinkingLogManager

class ThinkingAnimationHandler:
    """
    Handles the display and state management for the LLM's "thinking" animation.
    This class allows for different visual modes (dots, spinner, progress bar)
    and ensures that the special <think> and </think> tags are consumed
    and not printed to the console by robustly processing the raw token string
    using regular expressions and an internal buffer to account for fragmented tags.
    It can also log raw "thinking" tokens to a ThinkingLogManager instance.
    """

    SPINNER_CHARS = ['|', '/', '-', '\\']
    PROGRESS_BAR_LENGTH = 20
    THINKING_PREFIX = "Thinking"
    MAX_UNTILL_THINK_DRAW = 10
    MAX_THINKING_INDICATOR_LENGTH = len(THINKING_PREFIX + "... [" + '-' * PROGRESS_BAR_LENGTH + "]") + 1

    THINK_START_PATTERN = re.compile(r'\s*<think>\s*')
    THINK_END_PATTERN = re.compile(r'\s*</think>\s*')
    CONTROL_CHARS_PATTERN = re.compile(r'[\x00-\x09\x0B-\x1F\x7F]')

    PARTIAL_TAG_PATTERN = re.compile(r'<th(?:in(?:k>)?|/th(?:ink>)?|i|n|k|/i|/n|/k)?')


    def __init__(self, enable_display: bool = True, mode: str = "dots", log_manager: ThinkingLogManager = None, header_tags=""):
        """
        Initializes the ThinkingAnimationHandler.

        Args:
            enable_display (bool): If True, thinking animations are enabled.
            mode (str): The desired thinking animation mode ('dots', 'spinner', 'progressbar').
            log_manager (ThinkingLogManager, optional): An instance of ThinkingLogManager
                                                         to log raw thinking tokens. Defaults to None.
        """
        self.enable_display = enable_display
        self.mode = mode.lower()
        self._log_manager = log_manager

        self._is_thinking_active = False
        self._has_thinking_intro_printed = False
        self._current_thinking_count = 0
        self._token_accumulation_buffer = ""
        self._header_tags = header_tags


    def process_token_and_thinking_state(self, raw_token_string: str) -> tuple[bool, str]:
        """
        Processes a raw token string from the LLM stream.
        Manages the thinking animation display and returns the token content
        with <think> tags removed. It uses an internal buffer to handle fragmented tags.
        Also logs the raw token string if currently in a thinking state.

        Args:
            raw_token_string (str): The raw token string from the LLM.

        Returns:
            tuple[bool, str]:
                - bool: True if the handler is currently in a thinking state.
                - str: The token content to be printed (tags removed and internal
                       thought content suppressed). This will be an empty string
                       if in an active thinking phase or if the tag is consumed.
        """
        self._token_accumulation_buffer += raw_token_string
        cleaned_buffer = self.CONTROL_CHARS_PATTERN.sub('', self._token_accumulation_buffer)

        token_content_for_display = ""

        if not self.enable_display:
            display_content = self._token_accumulation_buffer
            self._token_accumulation_buffer = ""
            return self._is_thinking_active, display_content

        # --- Priority 1: Handle END tag ---
        end_match = self.THINK_END_PATTERN.search(cleaned_buffer)
        if end_match:
            if self._is_thinking_active:
                # Log the raw end tag content
                if self._log_manager:
                    self._log_manager.write_thinking_log(raw_token_string)

                content_after_end_tag = cleaned_buffer[end_match.end():]

                func.out("\r" + " " * self.MAX_THINKING_INDICATOR_LENGTH + "\r", end="", flush=True)
                func.out("\n", flush=True)
                
                self._is_thinking_active = False
                self._has_thinking_intro_printed = False
                self._current_thinking_count = 0

                self._token_accumulation_buffer = content_after_end_tag
                
                return self._is_thinking_active, ""
            else:
                self._token_accumulation_buffer = self.THINK_END_PATTERN.sub('', cleaned_buffer)


        # --- Priority 2: Handle START tag ---
        start_match = self.THINK_START_PATTERN.search(self._token_accumulation_buffer)
        if start_match:
            if not self._is_thinking_active:
                token_content_for_display = self._token_accumulation_buffer[:start_match.start()]

                self._is_thinking_active = True
                self._current_thinking_count = 0

                # Removed: Log session header here (moved to direct.py)
                # Removed: Log the raw start tag content here

                if not self._has_thinking_intro_printed:
                    func.out(self.THINKING_PREFIX + "...", end="", flush=True)
                    self._has_thinking_intro_printed = True

                self._token_accumulation_buffer = self._token_accumulation_buffer[start_match.end():]

                return self._is_thinking_active, token_content_for_display
            else:
                self._token_accumulation_buffer = self.THINK_START_PATTERN.sub('', self._token_accumulation_buffer)


        # --- Priority 3: If currently thinking, and no (or handled) tags found in buffer ---
        if self._is_thinking_active:
            self._current_thinking_count += 1
            # Log the raw token string if a log manager is provided and thinking is active
            if self._log_manager:
                self._log_manager.write_thinking_log(raw_token_string)

            if self._current_thinking_count % self.MAX_UNTILL_THINK_DRAW == 0:
                if self.mode == "dots":
                    func.out(".", end="", flush=True)
                elif self.mode == "spinner":
                    spinner_char = self.SPINNER_CHARS[(self._current_thinking_count // self.MAX_UNTILL_THINK_DRAW) % len(self.SPINNER_CHARS)]
                    func.out(f"\r{self.THINKING_PREFIX}... {spinner_char}", end="", flush=True)
                elif self.mode == "progressbar":
                    bar_fill_position = ((self._current_thinking_count // self.MAX_UNTILL_THINK_DRAW) - 1) % self.PROGRESS_BAR_LENGTH
                    bar = ['-'] * self.PROGRESS_BAR_LENGTH
                    bar[bar_fill_position] = '#'
                    progress_bar_str = '[' + ''.join(bar) + ']'
                    func.out(f"\r{self.THINKING_PREFIX}... {progress_bar_str}", end="", flush=True)
            
            return self._is_thinking_active, ""


        # --- Priority 4: Not thinking, and no tags found in current buffer ---
        if not self.PARTIAL_TAG_PATTERN.search(cleaned_buffer):
            token_content_for_display = self._token_accumulation_buffer
            self._token_accumulation_buffer = ""
            return self._is_thinking_active, token_content_for_display
        else:
            return self._is_thinking_active, ""
