import functions as func

class OutputPrinter:
    """
    Manages how LLM output tokens are printed to the console based on the print mode.
    Handles buffering for 'line' and 'every_x_tokens' modes.
    """
    def __init__(self, print_mode: str = "token", tokens_per_print: int = 5):
        self.print_mode = print_mode
        self.tokens_per_print = max(1, tokens_per_print)

        self.line_buffer = "" # Used for 'line' and 'line_or_x_tokens'
        self.token_buffer = "" # Used for 'every_x_tokens' and 'line_or_x_tokens' (conceptually, will use line_buffer for actual text)
        self.buffered_token_count = 0 # Used for 'every_x_tokens' and 'line_or_x_tokens'

    def process_and_print(self, token_to_display: str) -> None:
        """
        Processes a single formatted token and prints it based on the configured mode.
        """
        output_string = self.process_token(token_to_display)

        if output_string is not None:
            func.out(output_string, end="", flush=True)

        # The 'unknown print_mode' warning is now handled inside process_token.
        # No extra print needed here as it's returned by process_token if it happens.

    def flush_buffers(self) -> None:
        """
        Prints any remaining content in buffers at the end of the stream.
        """
        if self.print_mode == "line" and self.line_buffer:
            func.out(self.line_buffer, end="", flush=True)
            self.line_buffer = ""
        elif self.print_mode == "every_x_tokens" and self.token_buffer:
            func.out(self.token_buffer, end="", flush=True)
            self.token_buffer = ""
        elif self.print_mode == "line_or_x_tokens" and self.line_buffer:
            func.out(self.line_buffer, end="", flush=True)
            self.line_buffer = ""
            self.buffered_token_count = 0 # Reset count too

    def process_token(self, token_to_display: str) -> str:
        """
        Processes a single formatted token and returns the string to be printed,
        or None if nothing is ready to be printed yet (due to buffering).
        """
        if self.print_mode == "token":
            return token_to_display

        elif self.print_mode == "line":
            self.line_buffer += token_to_display
            if "\n" in self.line_buffer:
                parts = self.line_buffer.split("\n")
                temp = ""
                for i in range(len(parts) - 1):
                    temp += (parts[i] + "\n")
                self.line_buffer = parts[-1]
                return temp
            return None

        elif self.print_mode == "every_x_tokens":
            self.token_buffer += token_to_display
            self.buffered_token_count += 1
            if self.buffered_token_count >= self.tokens_per_print:
                temp = self.token_buffer
                self.token_buffer = ""
                self.buffered_token_count = 0
                return temp
            return None

        elif self.print_mode == "line_or_x_tokens":
            self.line_buffer += token_to_display
            self.buffered_token_count += 1

            output_ready = False
            output_string = ""

            # Check for newline first
            if "\n" in self.line_buffer:
                parts = self.line_buffer.split("\n")
                for i in range(len(parts) - 1):
                    output_string += (parts[i] + "\n")
                self.line_buffer = parts[-1]
                self.buffered_token_count = 0 # Reset count when a line is completed
                output_ready = True
            # If no newline, check for token limit
            elif self.buffered_token_count >= self.tokens_per_print:
                output_string = self.line_buffer
                self.line_buffer = ""
                self.buffered_token_count = 0 # Reset count when limit is hit
                output_ready = True

            return output_string if output_ready else None

        else:
            # Handle unknown print_mode by logging a warning and returning the token directly
            func.log(f"Warning: Unknown print_mode '{self.print_mode}'. Defaulting to 'token'.")
            return token_to_display