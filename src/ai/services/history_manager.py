import os
import json
from typing import Optional, Dict, List
from ai.chat.chat import Chat, ChatRoles
from ai.core.llms.base_llm import BaseModel
import ai.functions as func

class HistoryManager:
    """
    Manages chat history and persistence.
    Prevents duplication of messages and handles session resumption.
    """

    def __init__(self, chat: Chat):
        """
        Initializes the HistoryManager with a specific Chat instance.

        Args:
            chat: The Chat object whose message history will be managed.
        """
        self.chat = chat
        self.chat_filepath: Optional[str] = None
        self.thinking_log_filepath: Optional[str] = None
        self.workspace_path: Optional[str] = None

    def initialize_session(self, session_paths: Dict[str, str]):
        """
        Sets session context and triggers history loading on boot.

        Args:
            session_paths: A dictionary containing paths for the chat file,
                            thinking log, and workspace.
        """
        self.chat_filepath = session_paths.get("session_chat_filepath")
        self.thinking_log_filepath = session_paths.get("session_thinking_log_filepath")
        self.workspace_path = session_paths.get("session_workspace_path")
        
        self.load_history()

    def switch_active_session(self, new_chat_filepath: str):
        """
        Hot-swaps the active memory file for the server.
        Clears the current RAM context and loads the specified JSON.

        Args:
            new_chat_filepath: The path to the new chat history file to load.
        """
        if self.chat_filepath == new_chat_filepath:
            return # Already looking at the right file

        func.log(f"HistoryManager: Routing memory to {new_chat_filepath}", level="DEBUG")
        self.chat_filepath = new_chat_filepath
        
        self.chat.messages.clear() 
        self.load_history()
    # ==========================================

    def load_history(self):
        """
        Loads conversation from disk without creating duplicates.

        If the chat file does not exist, no action is taken.
        Messages already present in the current chat session are skipped during loading.
        """
        if not self.chat_filepath or not os.path.exists(self.chat_filepath):
            return

        try:
            with open(self.chat_filepath, "r", encoding="utf-8") as f:
                saved_messages = json.load(f)
            
            if not saved_messages:
                return

            existing_contents = {m.get("content") for m in self.chat.messages}
            
            for msg in saved_messages:
                if msg.get("content") in existing_contents:
                    continue
                self.chat.messages.append(msg)
            
            func.log(f"HistoryManager: Resumed history. Current message count: {len(self.chat.messages)}")
        except Exception as e:
            func.log(f"HistoryManager: History Load Error: {e}", level="WARN")

    def add_message(self, role: str, content: str):
        """
        Wraps content and adds it to the active session.

        Prevents adding a message if the content is empty or if it is identical
        to the last message already in the chat history.

        Args:
            role: The role of the message (e.g., 'user', 'assistant').
            content: The textual content of the message.
        """
        if not content or not content.strip():
            return
            
        message = BaseModel.create_message(role, content.strip())
        
        if self.chat.messages and self.chat.messages[-1].get("content") == message.get("content"):
            return

        self.chat.messages.append(message)

    def save(self):
        """
        Saves the current state of the chat memory to the configured disk path.

        If the chat_filepath is not set, no saving occurs.
        """
        if not self.chat_filepath:
            return
        try:
            os.makedirs(os.path.dirname(self.chat_filepath), exist_ok=True)
            with open(self.chat_filepath, "w", encoding="utf-8") as f:
                json.dump(self.chat.messages, f, indent=4)
        except Exception as e:
            func.log(f"HistoryManager: Save Failure: {e}", level="ERROR")

    def get_log_path(self) ->str:
        """
        Retrieves the path for the thinking log.

        If thinking_log_filepath is set, it returns that path; otherwise,
        it defaults to a standard location within the root directory.

        Returns:
            str: The determined path for the thinking log.
        """
        return self.thinking_log_filepath or func.get_root_directory() + "/logs/active_thinking.log"