from color import Color
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import json

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    stream: Optional[bool] = False
    temperature: Optional[float] = 0.7

def create_app(orchestrator):
    app = FastAPI(title="JARVIS Neural Hub")

    @app.get("/health")
    async def health():
        return {"status": "online", "model": getattr(orchestrator, 'model_chat_name', 'JARVIS')}

    @app.post("/v1/shutdown")
    async def shutdown():
        return {"status": "shutdown acknowledged"}

    @app.post("/v1/chat/completions")
    @app.post("/v1/chat")
    async def chat_completions(request: ChatCompletionRequest):
        if not orchestrator:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized.")

        # 1. NORMALIZE INPUT
        # Strip spaces and lowercase to ensure "Default" and "default" are seen as the same
        requested_model = (request.model or "default").strip().lower()
        system_prompt = request.system_prompt or ""

        # Use a specific attribute for tracking the LOADED config name, not the display name
        current_model_id = getattr(orchestrator, 'active_model_id', None)

        # 2. THE SMART SWAP LOGIC
        # Only reload if:
        # A) No LLM is currently in VRAM
        # B) The requested model ID is different from the active one
        if not getattr(orchestrator, 'llm', None) or current_model_id != requested_model:
            print(f"{Color.CYAN}[!] Neural Swap Initiated: '{current_model_id}' -> '{requested_model}'{Color.RESET}")
            try:
                # Trigger the load
                orchestrator.load(requested_model, system_prompt)
                
                # CRITICAL: Update the tracking ID so the next request knows it's already loaded
                orchestrator.active_model_id = requested_model
                
            except Exception as e:
                print(f"{Color.RED}Error loading model {requested_model}: {e}{Color.RESET}")
                raise HTTPException(status_code=500, detail=f"Failed to load model {requested_model}")
        else:
            # The Brain is already warm!
            print(f"{Color.GREEN}[ * ] Neural Link Persistent: '{requested_model}' is already active.{Color.RESET}")

        # 3. PROCEED TO INFERENCE
        formatted_messages = [{"role": m.role, "content": m.content} for m in request.messages]
        
        try:
            # Inference logic (assuming .chat returns an iterator/list)
            raw_output = orchestrator.llm.chat(formatted_messages, stream=True)
            response_text = "".join([str(chunk) for chunk in raw_output if chunk])

            return {
                "choices": [{
                    "message": {"role": "assistant", "content": response_text}
                }]
            }
        except Exception as e:
            print(f"{Color.RED}Inference Error: {e}{Color.RESET}")
            raise HTTPException(status_code=500, detail=str(e))
    return app