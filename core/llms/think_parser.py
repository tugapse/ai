import functions as func
from color import Color
import re # Import the regular expression module
# import sys # Keep for debugging if needed, remove for production

class ThinkingAnimationHandler:
    """
    Handles the display and state management for the LLM's "thinking" animation.
    This class allows for different visual modes (dots, spinner, progress bar)
    and ensures that the special <think> and </think> tags are consumed
    and not printed to the console by robustly processing the raw token string
    using regular expressions and an internal buffer to account for fragmented tags.
    """

    # Constants for thinking animation - now class-level attributes
    SPINNER_CHARS = ['|', '/', '-', '\\']
    PROGRESS_BAR_LENGTH = 20 # Limit progress bar to 20 characters
    THINKING_PREFIX = "Thinking" # Consistent prefix for thinking messages
    MAX_UNTILL_THINK_DRAW = 10 # Interval (in tokens) for updating the thinking indicator
    # Maximum possible length of the thinking indicator for clearing the line.
    # This assumes "Thinking... " + "[--------------------]" is the longest output.
    MAX_THINKING_INDICATOR_LENGTH = len(THINKING_PREFIX + "... [" + '-' * PROGRESS_BAR_LENGTH + "]") + 1

    # Regex patterns for robustness against hidden characters/whitespace
    # Matches <think> with optional whitespace/control chars around it
    THINK_START_PATTERN = re.compile(r'\s*<think>\s*')
    # Matches </think> with optional whitespace/control chars around it
    THINK_END_PATTERN = re.compile(r'\s*</think>\s*')
    # Pattern to remove common non-printable ASCII control characters (excluding newline \n and tab \t)
    CONTROL_CHARS_PATTERN = re.compile(r'[\x00-\x09\x0B-\x1F\x7F]')

    # New pattern to check for partial tag presence in the buffer
    # This will match if any part of "<think>" or "</think>" is seen.
    PARTIAL_TAG_PATTERN = re.compile(r'<th(?:in(?:k>)?|/th(?:ink>)?|i|n|k|/i|/n|/k)?')


    def __init__(self, enable_display: bool = True, mode: str = "dots", log_manager=None):
        """
        Initializes the ThinkingAnimationHandler.

        Args:
            enable_display (bool): If True, thinking animations are enabled.
            mode (str): The desired thinking animation mode ('dots', 'spinner', 'progressbar').
            log_manager (ThinkingLogManager, optional): An instance of ThinkingLogManager
                                                         to log raw thinking tokens. Defaults to None.
        """
        self.enable_display = enable_display
        self.mode = mode.lower() # Store mode in lowercase for consistent checking
        self._log_manager = log_manager # Store the log manager instance

        # Internal state variables
        self._is_thinking_active = False
        self._has_thinking_intro_printed = False
        self._current_thinking_count = 0 # Tracks tokens processed while thinking
        self._token_accumulation_buffer = "" # Buffer for fragmented tokens


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
        # Always append the new raw token to the accumulation buffer
        self._token_accumulation_buffer += raw_token_string
        # Clean the accumulated buffer from common control characters for robust tag detection
        cleaned_buffer = self.CONTROL_CHARS_PATTERN.sub('', self._token_accumulation_buffer)

        # Initialize content to return as empty for most cases during tag handling
        token_content_for_display = ""

        # DEBUGGING LINES START (Uncomment if needed for further debugging)
        # import sys
        # sys.stderr.write(f"DEBUG raw_token_string: {repr(raw_token_string)}\n")
        # sys.stderr.write(f"DEBUG accumulated_buffer: {repr(self._token_accumulation_buffer)}\n")
        # sys.stderr.write(f"DEBUG cleaned_buffer_for_search: {repr(cleaned_buffer)}\n")
        # DEBUGGING LINES END

        # If thinking display is not enabled, just return current state and the entire cleaned buffer
        if not self.enable_display:
            display_content = self._token_accumulation_buffer
            self._token_accumulation_buffer = "" # Clear buffer if display disabled, as content is passed through
            return self._is_thinking_active, display_content

        # --- Priority 1: Handle END tag ---
        end_match = self.THINK_END_PATTERN.search(cleaned_buffer)
        if end_match:
            if self._is_thinking_active: # Only process end tag if we were thinking
                content_after_end_tag = cleaned_buffer[end_match.end():]

                func.out("\r" + " " * self.MAX_THINKING_INDICATOR_LENGTH + "\r", end="", flush=True)
                func.out(self.THINKING_PREFIX + ". done\n", flush=True) # Ensure newline

                self._is_thinking_active = False
                self._has_thinking_intro_printed = False
                self._current_thinking_count = 0

                # The buffer now contains only the content that appeared AFTER the end tag.
                # This content will be processed and displayed in the *next* iteration.
                self._token_accumulation_buffer = content_after_end_tag
                # sys.stderr.write(f"DEBUG Buffer after END tag: {repr(self._token_accumulation_buffer)}\n") # Debug
                
                # Crucially, return empty string for display in this cycle,
                # as the "done" message has already taken care of the output.
                return self._is_thinking_active, ""
            else:
                # If end tag found but not thinking, it's an anomaly. Strip it.
                # The buffer will retain whatever is left after stripping.
                self._token_accumulation_buffer = self.THINK_END_PATTERN.sub('', cleaned_buffer)
                # sys.stderr.write(f"DEBUG END tag found but not thinking. Stripping tag. Buffer: {repr(self._token_accumulation_buffer)}\n") # Debug
                # Do NOT return here; fall through to see if a start tag follows or if content needs printing.


        # --- Priority 2: Handle START tag ---
        start_match = self.THINK_START_PATTERN.search(self._token_accumulation_buffer) # Search raw buffer here for start tag!
        if start_match:
            if not self._is_thinking_active: # Only process start tag if we were NOT thinking
                # Content before the start tag is actual LLM output and should be displayed.
                token_content_for_display = self._token_accumulation_buffer[:start_match.start()]
                # sys.stderr.write(f"DEBUG Content BEFORE START tag: {repr(token_content_for_display)}\n") # Debug

                self._is_thinking_active = True
                self._current_thinking_count = 0 # Reset count for new thinking block

                if not self._has_thinking_intro_printed:
                    func.out(self.THINKING_PREFIX + "...", end="", flush=True)
                    self._has_thinking_intro_printed = True

                # The buffer now contains only the content after the start tag (i.e., the thought content).
                # This thought content is consumed by the animation.
                self._token_accumulation_buffer = self._token_accumulation_buffer[start_match.end():]
                # sys.stderr.write(f"DEBUG Buffer after START tag: {repr(self._token_accumulation_buffer)}\n") # Debug

                # Return the content that was *before* the <think> tag.
                # All content *within* the thinking block will be suppressed.
                return self._is_thinking_active, token_content_for_display
            else:
                # If start tag found but already thinking, it's redundant. Strip it.
                # The buffer will retain whatever is left after stripping.
                self._token_accumulation_buffer = self.THINK_START_PATTERN.sub('', self._token_accumulation_buffer)
                # sys.stderr.write(f"DEBUG START tag found but already thinking. Stripping tag. Buffer: {repr(self._token_accumulation_buffer)}\n") # Debug
                # Do NOT return here; fall through to active thinking.


        # --- Priority 3: If currently thinking, and no (or handled) tags found in buffer ---
        # This means the current tokens are part of the internal thought process.
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
            
            # All accumulated content during active thinking (without a tag) is suppressed.
            # Crucially, DO NOT clear self._token_accumulation_buffer here.
            # It retains the thought content, which might include partial tags that
            # will be completed by future incoming tokens.
            # sys.stderr.write(f"DEBUG Active thinking, suppressing content. Buffer NOT cleared.\n") # Debug
            return self._is_thinking_active, "" # Always return empty string while actively thinking (no tags consumed)


        # --- Priority 4: Not thinking, and no tags found in current buffer ---
        # This is for normal output when not in a thinking state.
        # Only return/clear the buffer if no *potential* tags are still forming.
        if not self.PARTIAL_TAG_PATTERN.search(cleaned_buffer):
            token_content_for_display = self._token_accumulation_buffer
            self._token_accumulation_buffer = "" # Clear buffer after returning content
            # sys.stderr.write(f"DEBUG Not thinking, returning content: {repr(token_content_for_display)}\n") # Debug
            return self._is_thinking_active, token_content_for_display
        else:
            # If partial tag is present, don't return content and don't clear buffer.
            # Wait for more tokens to complete the tag.
            # sys.stderr.write(f"DEBUG Partial tag detected, buffering: {repr(cleaned_buffer)}\n") # Debug
            return self._is_thinking_active, "" # Return empty string, buffer persists
