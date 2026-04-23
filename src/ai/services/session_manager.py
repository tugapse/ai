import os
import time
from datetime import datetime
from typing import Dict, Any

import functions as func
from services.config_helper import ProgramConfig, ProgramSetting

class SessionManager:
    """
    Manages the creation of session-specific paths and timestamps.
    Updated to persist session IDs across rapid sequential calls (2-stage process).
    """

    @staticmethod
    def initialize_session_paths(config: ProgramConfig) -> Dict[str, str]:
        """
        Generates and ensures existence of session-specific directories and file paths.
        Now attempts to resume the most recent session if it's 'warm'.
        """
        logs_dir = config.get(ProgramSetting.PATHS_LOGS)
        session_id_pointer = os.path.join(logs_dir, "last_session.id")
        
        session_timestamp = None
        
        # --- SESSION PERSISTENCE LOGIC ---
        # If the last session started less than 5 minutes ago, reuse its ID.
        if os.path.exists(session_id_pointer):
            last_id = func.read_file(session_id_pointer).strip()
            file_mod_time = os.path.getmtime(session_id_pointer)
            
            if (time.time() - file_mod_time) < 300: # 5 minutes
                session_timestamp = last_id
                func.log(f"SessionManager: Resuming 'warm' session: {session_timestamp}")

        # If no warm session, create a new one
        if not session_timestamp:
            session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            func.write_to_file(session_id_pointer, session_timestamp)
            func.log(f"SessionManager: Initializing new session: {session_timestamp}")

        session_paths = {
            "session_timestamp": session_timestamp,
            "session_chat_filepath": None,
            "session_thinking_log_filepath": None,
            "session_workspace_path": None,
        }

        # --- Chat log setup ---
        chat_log_folder = config.get(ProgramSetting.PATHS_CHAT_LOG)
        if chat_log_folder:
            func.ensure_directory_exists(chat_log_folder)
            session_paths["session_chat_filepath"] = os.path.join(
                chat_log_folder, f"chat_history_{session_timestamp}.json"
            )
        else:
            func.log(f"Chat log path not configured.", level="WARNING")

        # --- Thinking Log setup ---
        think_logs_base_dir = os.path.join(logs_dir, "thinking")
        if think_logs_base_dir:
            func.ensure_directory_exists(think_logs_base_dir) 
            session_paths["session_thinking_log_filepath"] = os.path.join(
                think_logs_base_dir, f"llm_thinking_{session_timestamp}.log"
            )

        # --- Workspace setup ---
        generated_files_base_path = config.get(ProgramSetting.PATHS_WORKSPACES)
        if not generated_files_base_path:
            generated_files_base_path = os.path.join(func.get_root_directory(), "workspaces") 

        session_paths["session_workspace_path"] = os.path.join(generated_files_base_path, f"session_{session_timestamp}")
        func.ensure_directory_exists(session_paths["session_workspace_path"]) 

        # Update legacy global logs
        func.ACTIVE_LOG_FILENAME = os.path.join(logs_dir, "active_log_filename.log")
        func.SESSION_LOG_FILENAME = os.path.join(logs_dir, "logs", f"{session_timestamp}_log_filename.log")
        
        # Ensure the logs directory exists before writing these
        os.makedirs(os.path.dirname(func.SESSION_LOG_FILENAME), exist_ok=True)
        
        # Only clear active log if it's a truly new session (optional)
        # func.write_to_file(func.ACTIVE_LOG_FILENAME, "")
        
        return session_paths