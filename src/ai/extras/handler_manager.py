# handlers/manager.py

from typing import Optional, Tuple
from ai.extras.think_parser import ThinkingAnimationHandler
from ai.extras.thinking_log_manager import ThinkingLogManager 

class HandlerManager:
    """
    Manages the pipeline of token processing handlers.
    Simplified: Now focuses strictly on the Thinking/Animation state.
    """

    def __init__(self,
                 log_manager: ThinkingLogManager,
                 thinking_mode: str = "progressbar",
                 enable_thinking_display: bool = True,
                 show_thinking_animation: bool = False
                 ):
        
        # Initialize only the thinking handler
        self.thinking_handler: ThinkingAnimationHandler = ThinkingAnimationHandler(
            enable_display=enable_thinking_display,
            mode=thinking_mode,
            log_manager=log_manager,
            show_animation=show_thinking_animation
        )

    def process_token_chain(self, initial_token: str) -> Tuple[bool, str, Optional[str]]:
        """
        Processes a token to determine if it's a 'thought' or 'actual output'.
        
        Returns:
            Tuple[bool, str, None]:
            - display_to_user (bool): True if this is real output, False if it's a thought.
            - final_content (str): The text to show (empty if thinking).
            - file_content_saved (None): Kept as None to maintain signature compatibility.
        """
        # --- Stage 1: Thinking Logic ---
        is_thinking, content_from_thinking_handler = \
            self.thinking_handler.process_token_and_thinking_state(initial_token)

        if is_thinking:
            # While thinking, we suppress output to the console
            return False, "", None
        
        # If not thinking, we return the token (or the cleaned version) for display
        return True, content_from_thinking_handler, None