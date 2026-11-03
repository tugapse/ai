from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
import json

# Simple, explicit exceptions for session handling
class SessionError(Exception):
    """Base exception for session-related errors."""
    pass

class SessionNotFoundError(SessionError):
    """Raised when a requested session file does not exist."""
    pass

class InvalidPathError(SessionError):
    """Raised when a provided path would escape the root session directory."""
    pass

class SessionAccessError(SessionError):
    """Raised on generic access/IO errors while handling sessions."""
    pass


class SessionManager:
    """
    Manages the lifecycle of application sessions, allowing for loading, saving,
    listing, and deleting sessions stored as JSON files within a designated root directory.
    """
    def __init__(self, root_dir: Path, logger: Optional[Any] = None):
        """
        Initialize the session manager.

        Args:
            root_dir: Base directory where sessions are stored.
            logger: Optional logger/callback for debug/info messages. If provided, it should be callable accepting a string.
        """
        self.root_dir: Path = Path(root_dir).resolve()
        self.logger = logger

    def _log(self, message: str) -> None:
        """
        Internal helper to log messages if a logger callback is provided.

        Args:
            message: The string message to log.
        """
        if callable(self.logger):
            try:
                self.logger(message)
            except Exception:
                pass  # Avoid logging failures from breaking flow
        # If no logger provided, silently ignore

    def _resolve_session_path(self, session_path: str) -> Path:
        """
        Resolve a session path to an absolute JSON file within the root_dir.

        This prevents directory traversal outside the root.

        Args:
            session_path: The path string representing the session relative to the root directory.

        Returns:
            The resolved Path to the .json file corresponding to session_path.

        Raises:
            InvalidPathError: If the resolved path attempts to escape the root session directory.
        """
        path = (self.root_dir / session_path).with_suffix(".json")
        resolved = path.resolve()
        if not str(resolved).startswith(str(self.root_dir)):
            self._log(f"Invalid path access attempt: {resolved} is outside {self.root_dir}")
            raise InvalidPathError("Access outside allowed session directory")
        return resolved

    def list_sessions(self, session_folder: Optional[str] = None) -> List[Dict]:
        """
        List all sessions (metadata) under the root directory.
        Optionally filter by a sub-folder.

        Args:
            session_folder: Optional string specifying a sub-folder within the root_dir to search.

        Returns:
            A list of dictionaries, where each dictionary contains metadata for a session.
        """
        search_root_dir = self.root_dir
        if session_folder:
            search_root_dir = search_root_dir / session_folder

        if not search_root_dir.exists() or not search_root_dir.is_dir():
            return []

        session_entries: List[Tuple[Path, Dict]] = []
        try:
            for file_path in search_root_dir.rglob("*.json"):
                if file_path.is_file():
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            session_content = json.load(f)

                        session_metadata = {
                            "session_id": session_content.get("session_id"),
                            "session_folder": session_content.get("session_folder"),
                            "session_title": session_content.get("session_title"),
                            "last_updated": session_content.get("last_updated"),
                            "filename": str(file_path.relative_to(search_root_dir).with_suffix("")),
                        }
                        session_entries.append((file_path, session_metadata))
                        self._log(f"Loaded session metadata from: {file_path}")
                    except json.JSONDecodeError:
                        self._log(f"Skipping corrupted session file due to JSONDecodeError: {file_path}")
                    except Exception as e:
                        self._log(f"Error processing session file {file_path}: {e}")
        except Exception as e:
            self._log(f"Failed to read sessions: {e}")

        # Sort by file modification time, newest first
        session_entries.sort(key=lambda item: item[0].stat().st_mtime, reverse=True)
        sessions_to_return = [data for _, data in session_entries]
        return sessions_to_return

    def load_session(self, session_path: str) -> Dict:
        """
        Load a single session by its path.

        Args:
            session_path: The path string identifying the session file.

        Returns:
            A dictionary containing the full content of the session.

        Raises:
            InvalidPathError: If the path attempts to escape the root directory.
            SessionNotFoundError: If the specified session file does not exist.
            SessionError: If the session file is corrupted (JSON decoding error).
            SessionAccessError: If there are general IO errors reading the file.
        """
        try:
            resolved_file_path = self._resolve_session_path(session_path)
        except InvalidPathError as e:
            raise e

        if not resolved_file_path.exists() or not resolved_file_path.is_file():
            raise SessionNotFoundError(f"Session not found: {session_path}")

        try:
            with open(resolved_file_path, "r", encoding="utf-8") as f:
                content = json.load(f)
            content["filename"] = str(resolved_file_path.relative_to(self.root_dir).with_suffix(""))
            return content
        except json.JSONDecodeError:
            raise SessionError(f"Session file corrupted: {session_path}")
        except Exception as e:
            raise SessionAccessError(f"Error reading session {session_path}: {e}")

    def save_session(self, session_path: str, data: Dict) -> None:
        """
        Save (or overwrite) a session file with the provided data.

        Args:
            session_path: The path string where the session should be saved.
            data: The dictionary containing the session data to write.

        Raises:
            InvalidPathError: If the path attempts to escape the root directory.
            SessionAccessError: If there are general IO errors writing the file.
        """
        resolved_file_path = self._resolve_session_path(session_path)
        try:
            resolved_file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(resolved_file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            raise SessionAccessError(f"Failed to save session {session_path}: {e}")

    def update_session_content(self, session_path: str, content: Dict) -> None:
        """
        Overwrite the entire session content with the provided dict.

        Args:
            session_path: The path string identifying the session file to update.
            content: The new dictionary content to write to the session.

        Raises:
            SessionNotFoundError: If the specified session file does not exist.
            SessionAccessError: If there are general IO errors writing the file.
        """
        resolved_file_path = self._resolve_session_path(session_path)
        if not resolved_file_path.exists() or not resolved_file_path.is_file():
            raise SessionNotFoundError(f"Session not found: {session_path}")

        try:
            with open(resolved_file_path, "w", encoding="utf-8") as f:
                json.dump(content, f, indent=4)
        except Exception as e:
            raise SessionAccessError(f"Failed to update session {session_path}: {e}")

    def update_session_title(self, session_path: str, title: str) -> Dict:
        """
        Update only the session title field inside the JSON.

        Args:
            session_path: The path string identifying the session file.
            title: The new title string for the session.

        Returns:
            A dictionary confirming the status and the new title.

        Raises:
            SessionNotFoundError: If the specified session file does not exist.
            SessionError: If the session file is corrupted during the update.
            SessionAccessError: If there are general IO errors during the update.
        """
        resolved_file_path = self._resolve_session_path(session_path)
        if not resolved_file_path.exists() or not resolved_file_path.is_file():
            raise SessionNotFoundError(f"Session not found: {session_path}")

        try:
            with open(resolved_file_path, "r", encoding="utf-8") as f:
                session_data = json.load(f)

            old_title = session_data.get("session_title", "N/A")
            session_data["session_title"] = title

            with open(resolved_file_path, "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=4)

            return {"status": "success", "session_title": title}
        except json.JSONDecodeError:
            raise SessionError(f"Session file corrupted during title update: {session_path}")
        except Exception as e:
            raise SessionAccessError(f"Failed to update session title for {session_path}: {e}")

    def delete_session(self, session_path: str) -> None:
        """
        Delete a specific session file.

        Args:
            session_path: The path string identifying the session file to delete.

        Raises:
            SessionNotFoundError: If the specified session file does not exist.
            SessionAccessError: If there are general IO errors during deletion.
        """
        resolved_file_path = self._resolve_session_path(session_path)
        if not resolved_file_path.exists() or not resolved_file_path.is_file():
            raise SessionNotFoundError(f"Session not found: {session_path}")

        try:
            resolved_file_path.unlink()
        except Exception as e:
            raise SessionAccessError(f"Failed to delete session {session_path}: {e}")