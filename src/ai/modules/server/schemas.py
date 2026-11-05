from pydantic import BaseModel 
from typing import List, Optional, Dict, Any

class ChatMessage(BaseModel):
    """
    Represents a single message within a chat conversation.

    Attributes:
        role (str): The role of the sender (e.g., 'user', 'assistant').
        content (str): The textual content of the message.
    """
    role: str
    content: str

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
        temperature (Optional[float]): Controls the randomness of the output (0.0 to 1.0).
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
    temperature: Optional[float] = 0.7
    session_folder: Optional[str] = None
    session_id: Optional[str] = None
    session_title: Optional[str] = None

class UpdateSessionRequest(BaseModel):
    """
    Defines the structure for updating an existing chat session.

    Attributes:
        session_title (str): The new title for the session.
        session_content (Optional[List[ChatMessage]]): Optional list of messages to append or replace in the session.
    """
    session_title: str
    session_content: Optional[List[ChatMessage]] = None


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