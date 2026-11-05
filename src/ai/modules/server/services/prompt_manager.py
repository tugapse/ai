from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
import os

# Simple, explicit exceptions for prompt handling
class PromptError(Exception):
    """Base exception for prompt-related errors."""
    pass

class PromptNotFoundError(PromptError):
    """Raised when a requested prompt file does not exist."""
    pass

class InvalidPathError(PromptError):
    """Raised when a provided path would escape the root prompt directory."""
    pass

class PromptAccessError(PromptError):
    """Raised on generic access/IO errors while handling prompts."""
    pass


class PromptManager:
    """
    Manages the lifecycle of prompt files, allowing for listing, loading,
    saving, and deleting prompts within a specified root directory.

    This class enforces strict path validation to prevent directory traversal
    outside the designated prompt storage area.
    """
    def __init__(self, root_dir: Path, logger: Optional[Any] = None):
        """
        Initialize the prompt manager.

        Args:
            root_dir: Base directory where prompts are stored.
            logger: Optional logger/callback for debug/info messages.
        """
        self.root_dir: Path = Path(root_dir).resolve()
        self.logger = logger

    def _log(self, message: str) -> None:
        """
        Logs a message using the configured logger if one is provided.

        Args:
            message: The string message to log.
        """
        if callable(self.logger):
            try:
                self.logger(message)
            except Exception:
                pass  # Avoid logging failures from breaking flow

    def _resolve_prompt_path(self, prompt_path: str) -> Path:
        """
        Resolve a prompt path to an absolute Markdown file within the root_dir.
        This prevents directory traversal outside the root.

        Args:
            prompt_path: The path string relative to the root directory.

        Returns:
            The absolute Path object pointing to the resolved prompt file.

        Raises:
            InvalidPathError: If the path contains '..' or resolves outside the root_dir.
        """
        # Ensure the path is relative and does not contain '..'
        if ".." in prompt_path.split(os.path.sep):
            self._log(f"Invalid path component '..' in prompt path: {prompt_path}")
            raise InvalidPathError("Path cannot contain '..'")

        path = (self.root_dir / prompt_path).with_suffix(".md")
        resolved = path.resolve()
        
        if not str(resolved).startswith(str(self.root_dir)):
            self._log(f"Invalid path access attempt: {resolved} is outside {self.root_dir}")
            raise InvalidPathError("Access outside allowed prompt directory")
        return resolved

    def list_prompts(self, sub_folder: Optional[str] = None) -> List[Dict]:
        """
        List all prompts (as files) under the root directory.
        Optionally filter by a sub-folder.

        Args:
            sub_folder: Optional string specifying a subdirectory to search within.

        Returns:
            A list of dictionaries, where each dictionary contains the name, 
            path, and last modified time of a found prompt.
        
        Raises:
            PromptAccessError: If there is an IO error while reading the directory.
        """
        search_root_dir = self.root_dir
        if sub_folder:
            search_root_dir = search_root_dir / sub_folder

        if not search_root_dir.exists() or not search_root_dir.is_dir():
            return []

        prompt_entries: List[Dict] = []
        try:
            for file_path in search_root_dir.rglob("*.md"):
                if file_path.is_file():
                    relative_path = file_path.relative_to(self.root_dir)
                    prompt_data = {
                        "name": relative_path.stem,
                        "path": str(relative_path.with_suffix("")),
                        "last_modified": file_path.stat().st_mtime,
                    }
                    prompt_entries.append(prompt_data)
                    self._log(f"Found prompt: {file_path}")
        except Exception as e:
            self._log(f"Failed to read prompts: {e}")
            raise PromptAccessError(f"Failed to read prompts: {e}")

        # Sort by name
        prompt_entries.sort(key=lambda item: item["name"])
        return prompt_entries

    def load_prompt(self, prompt_path: str) -> str:
        """
        Load a single prompt by its path.

        Args:
            prompt_path: The path string identifying the prompt file.

        Returns:
            The full content of the prompt file as a string.

        Raises:
            PromptNotFoundError: If the specified prompt file does not exist.
            PromptAccessError: If there is an error reading the file.
        """
        resolved_file_path = self._resolve_prompt_path(prompt_path)

        if not resolved_file_path.exists() or not resolved_file_path.is_file():
            raise PromptNotFoundError(f"Prompt not found: {prompt_path}")

        try:
            with open(resolved_file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return content
        except Exception as e:
            raise PromptAccessError(f"Error reading prompt {prompt_path}: {e}")

    def save_prompt(self, prompt_path: str, content: str) -> None:
        """
        Save (or overwrite) a prompt file with the provided content.

        Args:
            prompt_path: The path string where the prompt should be saved.
            content: The string content to write to the file.

        Raises:
            PromptAccessError: If there is an error creating or writing the file.
        """
        resolved_file_path = self._resolve_prompt_path(prompt_path)
        try:
            resolved_file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(resolved_file_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            raise PromptAccessError(f"Failed to save prompt {prompt_path}: {e}")

    def read_prompt(self, prompt_path: str) -> str:
        """
        Backward-compatible alias for load_prompt.

        Args:
            prompt_path: The path string identifying the prompt file.

        Returns:
            The full content of the prompt file as a string.
        """
        return self.load_prompt(prompt_path)

    def create_prompt(self, prompt_path: str, content: str) -> Dict[str, str]:
        """
        Backward-compatible alias for saving a new prompt file.

        Args:
            prompt_path: The path string for the new prompt.
            content: The content to save in the new prompt.

        Returns:
            A dictionary confirming the creation message.
        """
        self.save_prompt(prompt_path, content)
        return {"message": f"Prompt '{prompt_path}' created successfully."}

    def update_prompt(self, prompt_path: str, content: str) -> Dict[str, str]:
        """
        Backward-compatible alias for updating an existing prompt file.

        Args:
            prompt_path: The path string of the prompt to update.
            content: The new content to overwrite the existing prompt with.

        Returns:
            A dictionary confirming the update message.
        """
        self.save_prompt(prompt_path, content)
        return {"message": f"Prompt '{prompt_path}' updated successfully."}

    def delete_prompt(self, prompt_path: str) -> None:
        """
        Delete a specific prompt file.

        Args:
            prompt_path: The path string of the prompt file to delete.

        Raises:
            PromptNotFoundError: If the specified prompt file does not exist.
            PromptAccessError: If there is an error deleting the file.
        """
        resolved_file_path = self._resolve_prompt_path(prompt_path)
        if not resolved_file_path.exists() or not resolved_file_path.is_file():
            raise PromptNotFoundError(f"Prompt not found: {prompt_path}")

        try:
            resolved_file_path.unlink()
        except Exception as e:
            raise PromptAccessError(f"Failed to delete prompt {prompt_path}: {e}")