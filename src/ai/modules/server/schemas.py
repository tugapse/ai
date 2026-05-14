from pydantic import BaseModel 
from typing import List, Optional, Dict, Any

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    stream: Optional[bool] = False
    temperature: Optional[float] = 0.7
    session_folder: Optional[str] = None
    session_id: Optional[str] = None
    session_title: Optional[str] = None

class UpdateSessionRequest(BaseModel):
    session_title: str
    session_content: Optional[List[ChatMessage]] = None


# --- Prompt Management Schemas ---

class Prompt(BaseModel):
    filename: str
    last_updated: float

class PromptData(Prompt):
    content: str

class PromptUpdateRequest(BaseModel):
    content: str

class PromptCreateRequest(BaseModel):
    prompt_path: str
    content: str
