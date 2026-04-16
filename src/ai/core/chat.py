import os
from datetime import datetime
from core.events import Events
from color import Color, format_text
import functions as func
from core.llms.base_llm import BaseModel
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.filters import Condition
from prompt_toolkit.completion import Completer, Completion

class ChatRoles:
    """
    Define constants for user roles in the chat.
    """
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    CONTROL = "control"
    TOOL = "tool"



class PrefixCompleter(Completer):
    def __init__(self, commands: list[str]):
        self.commands = commands

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        
        if text.startswith('/'):
            query = text[1:]
            for cmd in self.commands:
                if cmd.startswith(query):
                    yield Completion(cmd, start_position=-len(text))
        
        elif text.startswith('@'):
            query = text[1:]
            yield from self._file_completion(query)

    def _file_completion(self, query: str):
        # Handle trailing separator to allow directory browsing
        has_trailing_sep = query.endswith(os.sep)
        
        if has_trailing_sep:
            dirname, partial_name = query, ""
        else:
            parts = query.rsplit(os.sep, 1)
            if len(parts) == 2:
                dirname, partial_name = parts[0], parts[1]
            else:
                dirname, partial_name = "", query

        search_dir = dirname if dirname else "."
        
        if not os.path.isdir(search_dir):
            return

        try:
            for entry in os.scandir(search_dir):
                if not partial_name and not has_trailing_sep:
                    continue
                
                if not partial_name.startswith('.') and entry.name.startswith('.') and entry.name != '.' and entry.name != '..':
                    continue
                
                if entry.name.startswith(partial_name):
                    full_path = os.path.join(dirname, entry.name)
                    
                    # If it's a directory, ensure it ends with a separator for the next Tab press
                    if entry.is_dir():
                        display_path = full_path + os.sep
                        yield Completion(display_path, start_position=-len(query))
                    else:
                        yield Completion(full_path, start_position=-len(query))
        except PermissionError:
            pass



class Chat(Events):
    """
    Define the chat class that handles user input and outputs.
    """

    EVENT_CHAT_SENT = "chat_sent"
    EVENT_COMMAND_STARTED = "command_started"
    EVENT_OUTPUT_REQUESTED = "output_requested"
    EVENT_MESSAGES_UPDATED = "messages_updated"
    EVENT_AGENT_RUN_REQUESTED = "agent_run_requested"

    def __init__(self, commands: list[str] = None, agents: list[str] = None):
        super().__init__()
        self.terminate = False
        self.terminate_tokens = ["quit", "q"]
        self.running_command = False
        self.waiting_for_response = False
        self.messages = []
        self.images: list[str] = []
        self.current_message = ""
        self.user_prompt = "User: "
        self.assistant_prompt = ""
        self.max_chat_log = 50
        self.cache_messages = True
        self.current_prompt = ""
        self.session_chat_filepath = None
        
        self.multiline_mode = False
       
        # Completion setup
        self.commands = commands or []
        self.agents = agents or []
        self.attached_files: list[str] = [] # Track files separately
        self.completer = PrefixCompleter(self.commands)
        
        # New state for deferred file attachment
        self.pending_files: dict[str, str] = {} # {path: content}
        
        # Top Bar State
        self.top_bar_content: list[str] = [] # Array of strings for the top bar
        
        self.prompt_session = PromptSession(history=InMemoryHistory())
        self.kb = KeyBindings()
        self._setup_key_bindings()
        self.update_top_bar(["Initializing System"])


    def update_suggestions(self, commands: list[str] = None, agents: list[str] = None):
        """
        Updates the command and agent lists dynamically.
        """
        if commands is not None:
            self.commands = commands
        if agents is not None:
            self.agents = agents

    def update_top_bar(self, content_array: list[str]):
        """
        Updates the persistent top bar content.
        The content is right-aligned within the bar's display area.
        """
        self.top_bar_content = content_array

    def _setup_key_bindings(self):
        @self.kb.add('escape', 'enter')
        def _(event):
            self.multiline_mode = not self.multiline_mode

    def _get_top_bar_display(self):
        """
        Generates the formatted string for the top bar, right-aligned.
        """
        if not self.top_bar_content:
            return ""
        
        # Join content with a separator, then right-align it based on a standard width
        content_str = " | ".join(self.top_bar_content)
        # Assuming a reasonable maximum width for display purposes
        return ANSI(format_text(content_str, Color.WHITE))

    def _get_prompt_text(self):
        file_status = f" ({len(self.pending_files)} files pending)" if self.pending_files else ""
        
        # Prepend the top bar display logic here, though prompt_toolkit usually handles this via custom UI components.
        # For simplicity within the prompt text function, we'll just return the prompt, 
        # but the top bar logic is now available via _get_top_bar_display().
        
        if self.multiline_mode:
            return ANSI(format_text(f"User [Multiline]{file_status}: ", Color.BLUE))
        return ANSI(format_text(f"{self.user_prompt}{file_status}", Color.BLUE))

    def _get_bottom_toolbar(self):
        if self.waiting_for_response:
            return ANSI(format_text("  PROCESSING... THE ASSISTANT IS THINKING | Please wait. ", Color.YELLOW))
        if self.running_command:
            return ANSI(format_text("  COMMAND IN PROGRESS | System is executing task... ", Color.CYAN))
        if self.multiline_mode:
            return ANSI(format_text("  MULTI_LINE MODE ACTIVE | [Alt+Enter] to finish, [Enter] to send. ", Color.BLUE))
        
        pending_display = f" ({len(self.pending_files)} files pending)" if self.pending_files else ""
        return ANSI(format_text(f"  READY | [Enter] to send, or [Alt+Enter] for Multiline.{pending_display}", Color.WHITE))

    def _add_message(self, message_dict: dict):
        if self.cache_messages:
            self.messages.append(message_dict)
            self._check_messages_size(self.max_chat_log)

    def _reset_chat(self):
        self.messages = []
        self.pending_files = {} # Clear pending files on chat reset
        self.top_bar_content = [] # Clear top bar on chat reset

    def _check_messages_size(self, max_messages):
        if len(self.messages) > max_messages:
            self.messages.pop(0)

    def loop(self):
        while not self.terminate:
            self.process_loop_frame()

    def process_loop_frame(self):
        if not self.running_command and not self.waiting_for_response:
            try:
                user_input = self.prompt_session.prompt(
                    self._get_prompt_text,
                    multiline=Condition(lambda: self.multiline_mode),
                    key_bindings=self.kb,
                    bottom_toolbar=self._get_bottom_toolbar,
                    completer=self.completer,
                    complete_while_typing=True 
                )
            except (KeyboardInterrupt, EOFError):
                self.terminate_chat()
                return

            # Clear the line after input to prevent residual text from the previous prompt
            print("\r" + " " * 80 + "\r", end="") 

            user_input_stripped = user_input.strip()
            if not user_input_stripped:
                return

            # Handle File Attachment Logic (Deferred)
            if user_input_stripped.startswith('@'):
                self._handle_file_attachment(user_input_stripped)
                return

            self.multiline_mode = False
            if user_input_stripped.startswith("/"):
                self.run_command(user_input_stripped)
            else:
                # If there are pending files, combine them with the current message
                final_message_content = user_input_stripped
                if self.pending_files:
                    file_context = "\n\n--- Attached Files ---\n"
                    for path, content in self.pending_files.items():
                        file_context += f"File: {path}\nContent:\n{content}\n---\n"
                    final_message_content = file_context + user_input_stripped
                
                self.send_chat(final_message_content)
                # Clear pending files after sending
                self.pending_files = {}



    def _handle_file_attachment(self, input_text: str):
        file_path = input_text[1:].strip()
        if os.path.isfile(file_path):
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                # Store path and content in pending_files instead of sending immediately
                self.pending_files[file_path] = content
                func.out(format_text(f"File '{os.path.basename(file_path)}' staged for next message.", Color.YELLOW))
            except Exception as e:
                func.out(format_text(f"Error reading file: {e}", Color.RED))
        else:
            func.out(format_text("Invalid file path.", Color.RED))


    def send_chat(self, message_content: str):
        self.waiting_for_response = True
        self._add_message(BaseModel.create_message(ChatRoles.USER, message_content))
        func.out(format_text(self.assistant_prompt, Color.GREEN), end="", flush=True)
        self.trigger(self.EVENT_CHAT_SENT, message_content)

    def output_requested(self, message):
        self.trigger(self.EVENT_OUTPUT_REQUESTED, message)

    def start_command(self, message):
        self.trigger(self.EVENT_COMMAND_STARTED, message)

    def run_command(self, message):
        if message == "/clear":
            self._reset_chat()
            func.out(format_text("Chat history cleared.", Color.BLUE))
            self.running_command = False
        elif message.startswith("/agent"):
            parts = message.split(maxsplit=1)
            task = parts[1] if len(parts) > 1 else ""
            self.trigger(self.EVENT_AGENT_RUN_REQUESTED, task)
            self.running_command = False
        else:
            self.running_command = True
            self.start_command(message)

    def terminate_chat(self):
        self.terminate = True
        func.out(format_text("\nChat terminated.", Color.BLUE))

    def terminate_command(self):
        self.running_command = False

    def chat_finished(self):
        self.waiting_for_response = False  
        self._add_message(
            BaseModel.create_message(ChatRoles.ASSISTANT, self.current_message.strip())
        )
        self.current_message = ""  

    def save_chat_history(self, chat_log_folder=None):
        pass
