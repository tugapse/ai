from typing import Optional

from config import ProgramConfig, ProgramSetting
from extras.thinking_log_manager import ThinkingLogManager
from extras.output_printer import OutputPrinter
from extras import HandlerManager, ConsoleTokenFormatter
import functions as func

class UIOrchestrator:
    """
    Manages the visual and feedback components of the assistant.
    Responsible for:
    - Thinking/Thought process visualization (Progress bars).
    - Token buffering and console printing modes.
    - Handling 'Thinking' logs for debugging.
    - Console formatting (Markdown/Bolding).
    """

    def __init__(self, config: ProgramConfig):
        self.config = config
        
        # Core UI Components
        self.log_manager: Optional[ThinkingLogManager] = None
        self.printer: Optional[OutputPrinter] = None
        self.handler: Optional[HandlerManager] = None
        self.formatter = ConsoleTokenFormatter()

    def initialize(self, log_filepath: str):
        """
        Sets up the UI stack based on program configuration.
        """
        func.log("UIOrchestrator: Initializing display and feedback systems...")

        # 1. Setup the Thinking Log (The 'Brain' log)
        self.log_manager = ThinkingLogManager(log_file_name=log_filepath)

        # 2. Setup the Output Printer (Controls how fast text hits the screen)
        self.printer = OutputPrinter(
            print_mode=self.config.get(ProgramSetting.PRINT_MODE, "line_or_x_tokens"),
            tokens_per_print=self.config.get(ProgramSetting.TOKENS_PER_PRINT, 50)
        )

        # 3. Setup the Handler Manager (The Progress Bar and Thinking logic)
        self.handler = HandlerManager(
            log_manager=self.log_manager,
            thinking_mode=self.config.get(ProgramSetting.THINKING_MODE, "progressbar"),
            enable_thinking_display=self.config.get(ProgramSetting.ENABLE_THINKING_DISPLAY, True),
            show_thinking_animation=True
        )

        func.log("UIOrchestrator: Display systems active.")

    def reset_turn(self):
        """
        Clears formatting buffers at the start/end of a chat turn.
        """
        self.formatter.clear_process_token()
        if self.printer:
            self.printer.flush_buffers()

    def get_components(self):
        """
        Returns the trio of components needed by the StreamOrchestrator.
        """
        return {
            "printer": self.printer,
            "handler": self.handler,
            "formatter": self.formatter
        }