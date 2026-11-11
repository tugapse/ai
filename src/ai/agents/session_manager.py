import os
import json
import zlib
import base64
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

import ai.functions as func
from ai.services.directory_manager import DirectoryManager

class AgentSessionManager:
    """
    Manages persistence for agent sessions.
    Stored in: <system>/logs/agents/[hash]/[session_id].json
    """

    MANIFEST_FILE = "manifest.json"

    @staticmethod
    def _get_agents_storage_root() -> str:
        """
        Retrieves the root directory where all agent session data is stored.

        Returns:
            str: The absolute path to the agents storage root.
        """
        directory_manager = DirectoryManager()
        return os.path.join(directory_manager.get_system_logs_directory(), "agents")

    def __init__(self, session_id: str, working_directory: Optional[str] = None):
        """
        Initializes the session manager for a specific agent session.

        This sets up the necessary directory structure based on the working directory hash
        and prepares the path for the session's journal file.

        Args:
            session_id: A unique identifier for the current agent session.
            working_directory: The directory from which the agent session originated. 
                               Defaults to the current working directory if None.
        """
        # 1. User working dir (hashed)
        self.working_directory = os.path.normpath(os.path.abspath(working_directory or os.getcwd()))
        self.parent_dir = hashlib.sha256(self.working_directory.encode("utf-8")).hexdigest()[:16]
        self.session_id = session_id

        # 2. Base storage folder: system/logs/agents/<hash>
        self.storage_dir = os.path.join(self._get_agents_storage_root(), self.parent_dir)

        # 3. Session file: + session_id.json
        self.session_path = os.path.join(self.storage_dir, f"{self.session_id}.json")

        func.debug(f"AgentSessionManager: Init Hash='{self.parent_dir}' | Dir='{self.working_directory}'")
        self._ensure_storage()

    def _ensure_storage(self):
        """
        Ensures the agent folder and directory metadata manifest exist.

        Creates the storage directory if it does not exist and writes the manifest file
        containing metadata about the session's working directory.
        """
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir, exist_ok=True)
            func.log(f"AgentSessionManager: Created agent storage at {self.storage_dir}")
        else:
            func.debug(f"AgentSessionManager: Agent storage verified at {self.storage_dir}")

        manifest_path = os.path.join(self.storage_dir, self.MANIFEST_FILE)
        if not os.path.exists(manifest_path):
            try:
                manifest_payload = {
                    "working_directory": self.working_directory,
                    "hash": self.parent_dir,
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                with open(manifest_path, "w", encoding="utf-8") as f:
                    json.dump(manifest_payload, f, indent=2)
            except Exception as e:
                func.error(f"AgentSessionManager: Failed to write manifest: {str(e)}")

    def commit(self, orchestrator_state: Dict[str, Any], compress: bool = False):
        """
        Persists orchestrator state to the session's JSON journal.

        Each state update is appended as a new line to the session file. Compression
        can be enabled for larger state objects.

        Args:
            orchestrator_state: The current state dictionary of the orchestrator to save.
            compress: If True, the state data will be compressed using zlib and base64 encoded.
        """
        func.debug(f"AgentSessionManager: Committing state for {self.session_id}")

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

            with open(self.session_path, "a", encoding="utf-8") as f:
                f.write(data + "\n")
            
            func.log(f"AgentSessionManager: State committed to {self.session_path}")

        except Exception as e:
            func.error(f"AgentSessionManager: Commit failed for {self.session_id}: {str(e)}")
    
    def get_session(self, turn_index: int = -1) -> Optional[Dict[str, Any]]:
        """
        Re-inflates the orchestrator state from the agent file at a specific turn index.

        Args:
            turn_index: The zero-based index of the state entry to retrieve. Defaults to -1 (last entry).

        Returns:
            Optional[Dict[str, Any]]: The deserialized orchestrator state, or None if the file is missing or an error occurs.
        """
        if not os.path.exists(self.session_path):
            func.debug(f"AgentSessionManager: No state file found at {self.session_path}. Starting fresh.")
            return None

        func.log(f"AgentSessionManager: Hydrating from {self.session_path} (Index: {turn_index})")

        try:
            with open(self.session_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if not lines:
                    return None
                
                entry = json.loads(lines[turn_index])

                if entry.get("compressed"):
                    decompressed = zlib.decompress(base64.b64decode(entry["data"]))
                    state = json.loads(decompressed)["state"]
                else:
                    state = entry["state"]
                
                return state

        except Exception as e:
            func.error(f"AgentSessionManager: Hydration failed: {str(e)}")
            return None

    @staticmethod
    def get_working_directory_for_hash(hash_code: str) -> Optional[str]:
        """
        Resolves the original working directory from a parent directory hash code.

        This reads the manifest file associated with the given hash to find the original path.

        Args:
            hash_code: The 16-character SHA256 hash prefix representing the working directory.

        Returns:
            Optional[str]: The original working directory path, or None if the manifest is not found or readable.
        """
        manifest_path = os.path.join(AgentSessionManager._get_agents_storage_root(), hash_code, AgentSessionManager.MANIFEST_FILE)
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data.get("working_directory")
            except Exception:
                return None
        return None

    @staticmethod
    def list_all_projects() -> List[Dict[str, str]]:
        """
        Returns all tracked projects mapping their hash to the original working directory.

        Iterates through all subdirectories in the agents storage root and retrieves metadata
        from the manifest file of each directory.

        Returns:
            List[Dict[str, str]]: A list where each dictionary contains 'hash' and 'working_directory'.
        """
        agents_base = AgentSessionManager._get_agents_storage_root()
        if not os.path.exists(agents_base):
            return []

        projects = []
        for hash_dir in sorted(os.listdir(agents_base)):
            target = os.path.join(agents_base, hash_dir)
            if not os.path.isdir(target):
                continue
            
            working_dir = AgentSessionManager.get_working_directory_for_hash(hash_dir)
            projects.append({
                "hash": hash_dir,
                "working_directory": working_dir or "Unknown"
            })
        return projects

    @staticmethod
    def _extract_user_request_from_entry(entry: Dict[str, Any]) -> Optional[str]:
        """
        Extracts the initial user request from a committed session payload entry.

        It searches several common locations within the state dictionary (direct fields,
        history sequences, memory containers) for the first non-empty user message.

        Args:
            entry: A single JSON entry dictionary from the session file.

        Returns:
            Optional[str]: The extracted user request string, or None if not found.
        """
        state = entry.get("state", {}) if isinstance(entry, dict) else {}
        if not isinstance(state, dict):
            return None

        direct_value = state.get("user_request") or state.get("request") or state.get("prompt")
        if isinstance(direct_value, str) and direct_value.strip():
            return direct_value.strip()

        # [Truncated helper logic remains identical]
        def extract_from_sequence(items: Any) -> Optional[str]:
            if not isinstance(items, list): return None
            for item in items:
                if not isinstance(item, dict): continue
                if item.get("from") == "USER" and item.get("message"):
                    return str(item["message"]).strip()
                if item.get("role") == "user" and item.get("content"):
                    return str(item["content"]).strip()
            return None

        for container_name in ("agents", "memory"):
            container = state.get(container_name)
            if not isinstance(container, dict): continue
            for value in container.values():
                if isinstance(value, dict):
                    for key in ("history", "messages_received", "messages"):
                        message = extract_from_sequence(value.get(key))
                        if message: return message
                elif isinstance(value, list):
                    message = extract_from_sequence(value)
                    if message: return message

        top_level_history = state.get("history")
        message = extract_from_sequence(top_level_history)
        if message: return message

        return None

    @staticmethod
    def list_sessions(working_directory: Optional[str] = None) -> list:
        """
        Lists all agent sessions in the specified working directory.

        It scans the relevant storage directory, reads the first line of each session file,
        and attempts to extract the initial user request associated with that session.

        Args:
            working_directory: Optional path to filter sessions by their originating directory. 
                               Defaults to the current working directory.

        Returns:
            list: A list of dictionaries, each containing 'session_id', 'filename', and 'user_request'.
        """
        normalized_dir = os.path.normpath(os.path.abspath(working_directory or os.getcwd()))
        parent_dir = hashlib.sha256(normalized_dir.encode("utf-8")).hexdigest()[:16]

        storage_dir = os.path.join(AgentSessionManager._get_agents_storage_root(), parent_dir)

        func.debug(f"AgentSessionManager: Searching for sessions in '{storage_dir}'")

        if not os.path.exists(storage_dir):
            return []

        sessions = []
        for filename in sorted(os.listdir(storage_dir)):
            if not filename.endswith(".json") or filename == AgentSessionManager.MANIFEST_FILE:
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

    @staticmethod
    def _read_entry_state(line: str) -> Optional[Dict[str, Any]]:
        """Decodes one journal line (plain or compressed) into its state dict."""
        entry = json.loads(line)
        if entry.get("compressed"):
            entry = json.loads(zlib.decompress(base64.b64decode(entry["data"])))
        state = entry.get("state")
        return state if isinstance(state, dict) else None

    @staticmethod
    def list_sessions_detailed(working_directory: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Lists agent sessions for a working directory with metadata for pickers,
        most recently updated first.

        Args:
            working_directory: Directory the sessions originated from. Defaults to cwd.

        Returns:
            A list of dicts with 'session_id', 'user_request', 'last_user_message',
            'updated_at' (epoch seconds), 'turns' (committed states) and 'iteration'.
        """
        normalized_dir = os.path.normpath(os.path.abspath(working_directory or os.getcwd()))
        parent_dir = hashlib.sha256(normalized_dir.encode("utf-8")).hexdigest()[:16]
        storage_dir = os.path.join(AgentSessionManager._get_agents_storage_root(), parent_dir)
        if not os.path.isdir(storage_dir):
            return []

        sessions = []
        for filename in os.listdir(storage_dir):
            if not filename.endswith(".json") or filename == AgentSessionManager.MANIFEST_FILE:
                continue
            path = os.path.join(storage_dir, filename)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    lines = [line for line in f if line.strip()]
                updated_at = os.path.getmtime(path)
            except OSError:
                continue
            if not lines:
                continue

            last_state: Dict[str, Any] = {}
            try:
                last_state = AgentSessionManager._read_entry_state(lines[-1]) or {}
            except Exception:
                pass
            user_request = last_state.get("user_request")
            if not user_request:
                try:
                    user_request = AgentSessionManager._extract_user_request_from_entry(json.loads(lines[0]))
                except Exception:
                    user_request = None

            sessions.append({
                "session_id": filename[:-5],
                "user_request": user_request,
                "last_user_message": last_state.get("last_user_message") or user_request,
                "updated_at": updated_at,
                "turns": len(lines),
                "iteration": last_state.get("iteration", 0),
            })

        sessions.sort(key=lambda s: s["updated_at"], reverse=True)
        return sessions

    @staticmethod
    def extract_transcript(state: Optional[Dict[str, Any]], limit: int = 8) -> List[Dict[str, str]]:
        """
        Rebuilds the visible conversation (user messages and agent replies) from a saved state.

        Args:
            state: A session state as returned by ``get_session``.
            limit: Maximum number of most recent entries to return.

        Returns:
            A list of {'role': 'user'|'agent', 'agent': name, 'text': str}, oldest first.
        """
        if not state:
            return []
        agents = (state.get("memory") or {}).get("agents") or {}
        transcript: List[Dict[str, str]] = []
        for name, mem in agents.items():
            if not isinstance(mem, dict):
                continue
            for item in list(mem.get("history") or []) + list(mem.get("messages_received") or []):
                if not isinstance(item, dict):
                    continue
                if item.get("from") == "USER" and item.get("message"):
                    entry = {"role": "user", "agent": name, "text": str(item["message"])}
                elif item.get("from") == "SELF" and item.get("response"):
                    entry = {"role": "agent", "agent": name, "text": str(item["response"])}
                else:
                    continue
                # Delegated messages may be mirrored in several agents' memories.
                if not transcript or transcript[-1]["text"] != entry["text"]:
                    transcript.append(entry)
        return transcript[-limit:] if limit else transcript

    def get_history_summary(self) -> list:
        """
        Returns turn-by-turn summary for debugging purposes.

        Reads the entire session journal file and extracts key metadata (turn number, 
        timestamp, agent identity, and iteration count) from each committed state.

        Returns:
            list: A list of dictionaries summarizing each turn in the session.
        """
        if not os.path.exists(self.session_path):
            return []
        
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
                except Exception:
                    continue
        return history