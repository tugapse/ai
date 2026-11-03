from typing import Optional

from ai.services.config_helper import ProgramConfig, ProgramSetting
from ai.extras.thinking_log_manager import ThinkingLogManager
from ai.extras.output_printer import OutputPrinter
from ai.extras import HandlerManager, ConsoleTokenFormatter
import ai.functions as func

class UIOrchestrator:
    """
    Manages the visual and feedback components of the assistant.

    This class is responsible for coordinating all user-facing elements,
    including displaying the AI's thought process (e.g., progress bars),
    controlling how text is streamed to the console, and managing formatting.
    """

    def __init__(self, config: ProgramConfig):
        """
        Initializes the UIOrchestrator with the application configuration.

        Args:
            config: The ProgramConfig object containing global application settings.
        """
        self.config = config
        
        # Core UI Components
        self.log_manager: Optional[ThinkingLogManager] = None
        self.printer: Optional[OutputPrinter] = None
        self.handler: Optional[HandlerManager] = None
        self.formatter = ConsoleTokenFormatter()

    def initialize(self, log_filepath: str):
        """
        Sets up the UI stack based on program configuration.

        This method instantiates and configures the ThinkingLogManager, OutputPrinter,
        and HandlerManager using settings from the ProgramConfig.

        Args:
            log_filepath: The file path where the thinking process logs should be saved.
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

        This ensures that formatting state is reset before a new interaction begins.
        """
        self.formatter.clear_process_token()
        if self.printer:
            self.printer.flush_buffers()

    def get_components(self):
        """
        Returns the trio of components needed by the StreamOrchestrator.

        Returns:
            dict: A dictionary containing the initialized printer, handler, and formatter instances.
        """
        return {
            "printer": self.printer,
            "handler": self.handler,
            "formatter": self.formatter
        }