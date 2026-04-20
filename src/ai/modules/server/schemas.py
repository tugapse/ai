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
