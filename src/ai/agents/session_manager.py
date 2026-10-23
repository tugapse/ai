import os
import json
import zlib
import base64
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import ai.functions as func

class AgentSessionManager:
    """
    Manages persistence for agent sessions.
    Stored in: [root]/agents/[session_id].json
    """

    def __init__(self, session_id: str, working_directory: Optional[str] = None):
        """
        Initializes the session manager for a specific agent session.
        :param session_id: Unique identifier for the agent session.
        :param working_directory: Optional base directory for storage. Defaults to current working directory.
        """

        # sha256 the working directory to create a stable unique parent folder for agent sessions
        normalized_dir = os.path.abspath(working_directory or os.getcwd())
        self.parent_dir = hashlib.sha256(normalized_dir.encode("utf-8")).hexdigest()[:16]
        self.session_id = session_id
        self.storage_dir = os.path.join("logs", "agents", self.parent_dir)
        self.session_path = os.path.join(self.storage_dir, f"{self.session_id}.json")
    
        self._ensure_storage()

    def _ensure_storage(self):
        """Ensures the agents folder exists."""
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
            func.log(f"AgentSessionManager: Created agent storage at {self.storage_dir}")
        else:
            func.debug(f"AgentSessionManager: Agent storage verified at {self.storage_dir}")

    def commit(self, orchestrator_state: Dict[str, Any], compress: bool = False):
        """
        Persists orchestrator state to the session's JSON journal.
        """
        func.debug(f"AgentSessionManager: Committing state for {self.session_id} (Iter: {orchestrator_state.get('iteration')})")

        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "state": orchestrator_state,
            "version": "1.0"
        }

        try:
            data = json.dumps(payload)
            if compress:
                compressed_data = base64.b64encode(zlib.compress(data.encode())).decode()
                payload = {"compressed": True, "data": compressed_data, "timestamp": payload["timestamp"]}
                data = json.dumps(payload)

            # Use append mode to maintain a history (JSONL style despite .json extension)
            with open(self.session_path, "a", encoding="utf-8") as f:
                f.write(data + "\n")
            
            func.log(f"AgentSessionManager: State committed to {self.session_path}")

        except Exception as e:
            func.error(f"AgentSessionManager: Commit failed for {self.session_id}: {str(e)}")
    
    def get_session(self, turn_index: int = -1) -> Optional[Dict[str, Any]]:
        """
        Re-inflates the orchestrator from the agent file.
        """
        if not os.path.exists(self.session_path):
            func.debug(f"AgentSessionManager: No state file found at {self.session_path}. Starting fresh.")
            return None

        func.log(f"AgentSessionManager: Hydrating from {self.session_path} (Index: {turn_index})")

        try:
            with open(self.session_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if not lines: return None
                
                entry = json.loads(lines[turn_index])

                if entry.get("compressed"):
                    decompressed = zlib.decompress(base64.b64decode(entry["data"]))
                    state = json.loads(decompressed)["state"]
                else:
                    state = entry["state"]
                
                func.log(f"AgentSessionManager: Hydration successful. Resuming {state.get('current_agent')}")
                return state

        except Exception as e:
            func.error(f"AgentSessionManager: Hydration failed: {str(e)}")
            return None
    
    
    @staticmethod
    def _extract_user_request_from_entry(entry: Dict[str, Any]) -> Optional[str]:
        """Extracts the initial user request from a committed session payload."""
        state = entry.get("state", {}) if isinstance(entry, dict) else {}
        if not isinstance(state, dict):
            return None

        direct_value = state.get("user_request") or state.get("request") or state.get("prompt")
        if isinstance(direct_value, str) and direct_value.strip():
            return direct_value.strip()

        def extract_from_sequence(items: Any) -> Optional[str]:
            if not isinstance(items, list):
                return None
            for item in items:
                if not isinstance(item, dict):
                    continue
                if item.get("from") == "USER" and item.get("message"):
                    return str(item["message"]).strip()
                if item.get("role") == "user" and item.get("content"):
                    return str(item["content"]).strip()
            return None

        for container_name in ("agents", "memory"):
            container = state.get(container_name)
            if not isinstance(container, dict):
                continue

            for value in container.values():
                if isinstance(value, dict):
                    for key in ("history", "messages_received", "messages"):
                        message = extract_from_sequence(value.get(key))
                        if message:
                            return message
                elif isinstance(value, list):
                    message = extract_from_sequence(value)
                    if message:
                        return message

        top_level_history = state.get("history")
        message = extract_from_sequence(top_level_history)
        if message:
            return message

        return None

    @staticmethod
    def list_sessions(working_directory: str) -> list:
        """Lists all agent sessions in the specified working directory."""
        normalized_dir = os.path.abspath(working_directory or os.getcwd())
        parent_dir = hashlib.sha256(normalized_dir.encode("utf-8")).hexdigest()[:16]
        storage_dir = os.path.join("logs", "agents", parent_dir)

        if not os.path.exists(storage_dir):
            return []

        sessions = []
        for filename in sorted(os.listdir(storage_dir)):
            if not filename.endswith(".json"):
                continue

            session_id = filename[:-5]
            session_path = os.path.join(storage_dir, filename)
            user_request = None

            try:
                with open(session_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                            user_request = AgentSessionManager._extract_user_request_from_entry(entry)
                            if user_request:
                                break
                        except json.JSONDecodeError:
                            continue
            except OSError:
                user_request = None

            sessions.append({
                "session_id": session_id,
                "filename": session_id,
                "user_request": user_request,
            })

        return sessions

    def get_history_summary(self) -> list:
        """Returns turn-by-turn summary for debugging."""
        if not os.path.exists(self.session_path): return []
        
        history = []
        with open(self.session_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                try:
                    entry = json.loads(line)
                    state = entry.get("state", {})
                    history.append({
                        "turn": i,
                        "timestamp": entry["timestamp"],
                        "agent": state.get("current_agent", "UNKNOWN"),
                        "iteration": state.get("iteration")
                    })
                except: continue
        return history