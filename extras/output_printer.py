
import functions as func

class OutputPrinter:
    """
    Manages how LLM output tokens are printed to the console based on the print mode.
    Handles buffering for 'line' and 'every_x_tokens' modes.
    """
    def __init__(self, print_mode: str = "token", tokens_per_print: int = 5):
        self.print_mode = print_mode
        self.tokens_per_print = max(1, tokens_per_print)

        self.line_buffer = ""
        self.token_buffer = ""
        self.buffered_token_count = 0

    def process_and_print(self, token_to_display: str) -> None:
        """
        Processes a single formatted token and prints it based on the configured mode.
        """
        if self.print_mode == "token":
            func.out(token_to_display, end="", flush=True)
        elif self.print_mode == "line":
            self.line_buffer += token_to_display
            if "\n" in self.line_buffer:
                parts = self.line_buffer.split("\n")
                for i in range(len(parts) - 1):
                    func.out(parts[i] + "\n", end="", flush=True)
                self.line_buffer = parts[-1]
        elif self.print_mode == "every_x_tokens":
            self.token_buffer += token_to_display
            self.buffered_token_count += 1
            if self.buffered_token_count >= self.tokens_per_print:
                func.out(self.token_buffer, end="", flush=True)
                self.token_buffer = ""
                self.buffered_token_count = 0
        else:
            func.log(f"Warning: Unknown print_mode '{self.print_mode}'. Defaulting to 'token'.")
            func.out(token_to_display, end="", flush=True)

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


    def process_token(self, token_to_display: str) -> str:
        """
        Processes a single formatted token and prints it based on the configured mode.
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
                self.token_buffer = ""
                self.buffered_token_count = 0
                return (self.token_buffer)
            return None
        else:
            func.log(f"Warning: Unknown print_mode '{self.print_mode}'. Defaulting to 'token'.")
            return (token_to_display)
