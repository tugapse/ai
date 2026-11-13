import re

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any

MAX_IMAGES_PER_MESSAGE = 4
MAX_IMAGE_BYTES = 10 * 1024 * 1024
_IMAGE_DATA_URL = re.compile(r"^data:image/(png|jpeg|jpg|webp|gif);base64,[A-Za-z0-9+/=\s]+$")


class ChatMessage(BaseModel):
    """
    Represents a single message within a chat conversation.

    Attributes:
        role (str): The role of the sender (e.g., 'user', 'assistant').
        content (str): The textual content of the message.
        images (Optional[List[str]]): Image data URLs (png, jpeg, webp, gif). Only the last
            user message's images reach the model.
    """
    role: str
    content: str
    images: Optional[List[str]] = None

    @field_validator("images")
    @classmethod
    def _check_images(cls, images):
        if not images:
            return None
        if len(images) > MAX_IMAGES_PER_MESSAGE:
            raise ValueError(f"At most {MAX_IMAGES_PER_MESSAGE} images per message.")
        for image in images:
            if not _IMAGE_DATA_URL.match(image):
                raise ValueError("Images must be data URLs: data:image/<png|jpeg|webp|gif>;base64,...")
            if (len(image) - image.index(",") - 1) * 3 // 4 > MAX_IMAGE_BYTES:
                raise ValueError(f"Each image must be at most {MAX_IMAGE_BYTES // (1024 * 1024)} MB.")
        return images

class ChatCompletionRequest(BaseModel):
    """
    Defines the structure for a request to generate a chat completion.

    Attributes:
        messages (List[ChatMessage]): The sequence of messages in the conversation history.
        model (Optional[str]): The name of the AI model to use.
        model_config_data (Optional[Dict[str, Any]]): Optional configuration data for the model.
        system_prompt (Optional[str]): A general system instruction prompt.
        system_prompt_filename (Optional[str]): Filename path for a system prompt.
        system_prompt_content (Optional[str]): Direct content for the system prompt.
        stream (Optional[bool]): If True, the response will be streamed.
        temperature, top_p, top_k, max_tokens: Optional sampling settings for this request only.
            They override the model config; a field left out keeps the config value.
        session_folder (Optional[str]): Directory path for session storage.
        session_id (Optional[str]): Unique identifier for the current session.
        session_title (Optional[str]): Title assigned to the current session.
    """
    messages: List[ChatMessage]
    model: Optional[str] = None
    model_config_data: Optional[Dict[str, Any]] = None
    system_prompt: Optional[str] = None
    system_prompt_filename: Optional[str] = None
    system_prompt_content: Optional[str] = None
    stream: Optional[bool] = False
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    top_p: Optional[float] = Field(None, gt=0.0, le=1.0)
    top_k: Optional[int] = Field(None, ge=0)
    max_tokens: Optional[int] = Field(None, ge=1)
    session_folder: Optional[str] = None
    session_id: Optional[str] = None
    session_title: Optional[str] = None

class UpdateSessionRequest(BaseModel):
    """
    Defines the structure for updating an existing chat session.

    Attributes:
        session_title (Optional[str]): The new title (required by the /title route).
        session_content: For the content route: the whole session object (a dict with a
            ``messages`` list), or a bare message list that replaces only ``messages``.
    """
    session_title: Optional[str] = None
    session_content: Optional[Any] = None


# --- Prompt Management Schemas ---

class Prompt(BaseModel):
    """
    Represents metadata for a stored prompt file.

    Attributes:
        filename (str): The name or path of the prompt file.
        last_updated (float): A timestamp indicating when the prompt was last modified.
    """
    filename: str
    last_updated: float

class PromptData(Prompt):
    """
    Represents the complete data structure for a prompt, including its content.

    Attributes:
        filename (str): The name or path of the prompt file.
        last_updated (float): A timestamp indicating when the prompt was last modified.
        content (str): The actual text content of the prompt.
    """
    content: str

class PromptUpdateRequest(BaseModel):
    """
    Defines the structure for updating the content of an existing prompt.

    Attributes:
        content (str): The new content to set for the prompt.
    """
    content: str

class PromptCreateRequest(BaseModel):
    """
    Defines the structure for creating a new prompt file.

    Attributes:
        prompt_path (str): The file path where the new prompt should be saved.
        content (str): The initial content for the new prompt.
    """
    prompt_path: str
    content: str