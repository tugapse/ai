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
        self.chat = chat
        self.chat_filepath: Optional[str] = None
        self.thinking_log_filepath: Optional[str] = None
        self.workspace_path: Optional[str] = None

    def initialize_session(self, session_paths: Dict[str, str]):
        """
        Sets session context and triggers history loading on boot.
        """
        self.chat_filepath = session_paths.get("session_chat_filepath")
        self.thinking_log_filepath = session_paths.get("session_thinking_log_filepath")
        self.workspace_path = session_paths.get("session_workspace_path")
        
        self.load_history()

    def switch_active_session(self, new_chat_filepath: str):
        """
        Hot-swaps the active memory file for the server.
        Clears the current RAM context and loads the specified JSON.
        """
        if self.chat_filepath == new_chat_filepath:
            return # Already looking at the right file

        func.log(f"HistoryManager: Routing memory to {new_chat_filepath}", level="DEBUG")
        self.chat_filepath = new_chat_filepath
        
        self.chat.messages.clear() 
        self.load_history()
    # ==========================================

    def load_history(self):
        """Loads conversation from disk without creating duplicates."""
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
        """Wraps content and adds it to the active session."""
        if not content or not content.strip():
            return
            
        message = BaseModel.create_message(role, content.strip())
        
        if self.chat.messages and self.chat.messages[-1].get("content") == message.get("content"):
            return

        self.chat.messages.append(message)

    def save(self):
        """Saves memory to disk."""
        if not self.chat_filepath:
            return
        try:
            os.makedirs(os.path.dirname(self.chat_filepath), exist_ok=True)
            with open(self.chat_filepath, "w", encoding="utf-8") as f:
                json.dump(self.chat.messages, f, indent=4)
        except Exception as e:
            func.log(f"HistoryManager: Save Failure: {e}", level="ERROR")

    def get_log_path(self) ->str:
        return self.thinking_log_filepath or func.get_root_directory() + "/logs/active_thinking.log"