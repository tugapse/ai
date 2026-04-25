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
        if callable(self.logger):
            try:
                self.logger(message)
            except Exception:
                pass  # Avoid logging failures from breaking flow

    def _resolve_prompt_path(self, prompt_path: str) -> Path:
        """
        Resolve a prompt path to an absolute Markdown file within the root_dir.
        This prevents directory traversal outside the root.
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
        """
        resolved_file_path = self._resolve_prompt_path(prompt_path)
        try:
            resolved_file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(resolved_file_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            raise PromptAccessError(f"Failed to save prompt {prompt_path}: {e}")

    def delete_prompt(self, prompt_path: str) -> None:
        """
        Delete a specific prompt file.
        """
        resolved_file_path = self._resolve_prompt_path(prompt_path)
        if not resolved_file_path.exists() or not resolved_file_path.is_file():
            raise PromptNotFoundError(f"Prompt not found: {prompt_path}")

        try:
            resolved_file_path.unlink()
        except Exception as e:
            raise PromptAccessError(f"Failed to delete prompt {prompt_path}: {e}")