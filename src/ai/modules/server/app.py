import os
import json
from color import Color
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Any
from .brain_hub import BrainHub

import functions as func

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

def create_app(brain_hub: BrainHub, config: Any):
    app = FastAPI(title="JARVIS Neural Hub")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health():
        return {"status": "online", "model": getattr(brain_hub.get_stats(), 'model_chat_name', 'JARVIS')}

    @app.post("/v1/shutdown")
    async def shutdown():
        if brain_hub:
            brain_hub.unload_brain()
        func.log("Neural Hub shutdown requested via API.")
        return {"status": "shutdown acknowledged"}
    
    @app.get("/v1/sessions")
    async def get_sessions(session_folder: Optional[str] = None):
        """
        Retrieves a list of all saved session IDs.
        Optionally filters by a specific sub-folder.
        """
        session_dir = os.path.join(func.get_root_directory(), "logs", "server", "sessions")
        
        if session_folder:
            session_dir = os.path.join(session_dir, session_folder)
            
        if not os.path.exists(session_dir):
            return {"sessions": []}
            
        try:
            files = os.listdir(session_dir)
            
            session_files = [
                f for f in files if f.endswith(".json")
            ]
            
            session_files.sort(
                key=lambda x: os.path.getmtime(os.path.join(session_dir, x)), 
                reverse=True
            )
            
            session_ids = [f.replace(".json", "") for f in session_files]
            
            return {"sessions": session_ids}
            
        except Exception as e:
            print(f"{Color.RED}Failed to read sessions: {e}{Color.RESET}")
            raise HTTPException(status_code=500, detail="Internal server error reading session files.")

    @app.post("/v1/chat/completions")
    @app.post("/v1/chat")
    async def chat_completions(request: ChatCompletionRequest):
        if not brain_hub:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized.")

        # Resolve session directory and ensure it exists
        session_dir = os.path.join(func.get_root_directory(), "logs", "server", "sessions")
        if request.session_folder:
            session_dir = os.path.join(session_dir, request.session_folder)
        
        os.makedirs(session_dir, exist_ok=True)

        # Fallback to the active session state if no ID is provided by the client
        # Note: Replace "ACTIVE_SESSION" with your specific ProgramSetting enum if applicable
        target_session_id = request.session_id or config.get("ACTIVE_SESSION", "default")
        session_file = os.path.join(session_dir, f"{target_session_id}.json")

        # Note: Replace "PRINT_DEBUG" with your specific ProgramSetting enum (e.g., ProgramSetting.PRINT_DEBUG)
        if config.get("PRINT_DEBUG"):
            print(f"{Color.YELLOW}[DEBUG] Routing memory to: {session_file}{Color.RESET}")
        brain_hub.route_memory(session_file)
        requested_model = (request.model or "default").strip().lower()
        system_prompt = request.system_prompt or ""
        brain_hub.get_brain(requested_model, system_prompt)

        formatted_messages = [{"role": m.role, "content": m.content} for m in request.messages]
        
        if request.stream:
            async def event_generator():
                try:
                    raw_output = brain_hub.orchestrator.llm.chat(formatted_messages, stream=True)
                    
                    if config.get("PRINT_LOG"):
                        func.log("Streaming response initiated...")
                        
                    for chunk in raw_output:
                        if chunk:
                            payload = {"choices": [{"delta": {"content": str(chunk)}}]}
                            yield f"data: {json.dumps(payload)}\n\n"
                            
                    if config.get("PRINT_LOG"):
                        func.log("Streaming response completed.")
                    yield "data: [DONE]\n\n"

                except Exception as e:
                    print(f"{Color.RED}Streaming Error: {e}{Color.RESET}")
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
            return StreamingResponse(event_generator(), media_type="text/event-stream")
        
        else:
            try:
                raw_output = brain_hub.orchestrator.llm.chat(formatted_messages, stream=False)
                
                if isinstance(raw_output, str):
                    response_text = raw_output
                else:
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