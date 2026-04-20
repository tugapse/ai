from pydantic import BaseModel as PydanticBase
from typing import List, Optional, Dict, Any

class ChatRequest(PydanticBase):
    model_id: str
    messages: List[Dict[str, str]]
    system_prompt: Optional[str] = None
    stream: bool = True
    options: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None
    session_folder: Optional[str] = None
    session_title: Optional[str] = None



class ServerStatus(PydanticBase):
    status: str
    active_model: Optional[str]
    vram_usage: str # Placeholder for hardware check
    token_stats: Dict[str, Any]

class ModelListItem(PydanticBase):
    id: str
    name: str