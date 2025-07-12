# services/session_manager.py

import os
from datetime import datetime
from typing import Dict, Any

import functions as func
from config import ProgramConfig, ProgramSetting

class SessionManager:
    """
    Manages the creation of session-specific paths and timestamps.
    """

    @staticmethod
    def initialize_session_paths(config: ProgramConfig) -> Dict[str, str]:
        """
        Generates and ensures existence of session-specific directories and file paths.
        """
        session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        func.log(f"Initializing session at: {session_timestamp}") 
        
      

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
            func.log(f"Session chat history will be saved to: {session_paths['session_chat_filepath']}") 
        else:
            func.log(f"Chat log path is not configured. Chat history will not be saved. Check '{ProgramSetting.PATHS_CHAT_LOG}' in your config.", level="WARNING") 

        # --- Thinking Log setup ---
        think_logs_base_dir = os.path.join(config.get(ProgramSetting.PATHS_LOGS), "thinking")
        if think_logs_base_dir:
            func.ensure_directory_exists(think_logs_base_dir) 
            session_paths["session_thinking_log_filepath"] = os.path.join(
                think_logs_base_dir, f"llm_thinking_{session_timestamp}.log"
            )
            func.log(f"Thinking logs will be saved to: {session_paths['session_thinking_log_filepath']}") 
        else:
            func.log("Base logs directory not configured. Thinking logs will not be saved.", level="WARNING") 


        # --- Workspace setup for generated files ---
        generated_files_base_path = config.get(ProgramSetting.PATHS_WORKSPACES)
        if not generated_files_base_path:
            generated_files_base_path = os.path.join(func.get_root_directory(), "workspaces") 
            func.log(f"'{ProgramSetting.PATHS_WORKSPACES}' not found in config. Using fallback: {generated_files_base_path}", level="WARNING") 

        session_paths["session_workspace_path"] = os.path.join(generated_files_base_path, f"session_{session_timestamp}")
        func.ensure_directory_exists(session_paths["session_workspace_path"]) 
        func.log(f"Session workspace will be: {session_paths['session_workspace_path']}") 

        func.ACTIVE_LOG_FILENAME = os.path.join(config.get(ProgramSetting.PATHS_LOGS),"active_log_filename.log")
        func.SESSION_LOG_FILENAME = os.path.join(config.get(ProgramSetting.PATHS_LOGS),"logs",f"{session_timestamp}_log_filename.log")
        func.write_to_file(func.ACTIVE_LOG_FILENAME,"")
        func.write_to_file(func.SESSION_LOG_FILENAME,"",func.FILE_MODE_APPEND)
        return session_paths

