from color import Color
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware # <--- ADDED: Import CORS Middleware
from pydantic import BaseModel
from typing import List, Optional
from .brain_hub import BrainHub
import json

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

    
def create_app(brain_hub : BrainHub):
    app = FastAPI(title="JARVIS Neural Hub")

    # --- ADDED: CORS Configuration ---
    # This allows your Angular client (e.g., http://localhost:4200) to connect to this API
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allows all origins
        allow_credentials=True,
        allow_methods=["*"],  # Allows all methods including the OPTIONS preflight
        allow_headers=["*"],  # Allows all headers
    )
    # ---------------------------------

    @app.get("/health")
    async def health():
        return {"status": "online", "model": getattr(brain_hub.get_stats(), 'model_chat_name', 'JARVIS')}

    @app.post("/v1/shutdown")
    async def shutdown():
        if brain_hub:
            brain_hub.unload_brain()
        func.log("Neural Hub shutdown requested via API.")
        return {"status": "shutdown acknowledged"}

    @app.post("/v1/chat/completions")
    @app.post("/v1/chat")
    async def chat_completions(request: ChatCompletionRequest):
        if not brain_hub :
            raise HTTPException(status_code=503, detail="Orchestrator not initialized.")
        # 1. NORMALIZE INPUT
        requested_model = (request.model or "default").strip().lower()
        system_prompt = request.system_prompt or ""
        # current_model_id = getattr(orchestrator, 'active_model_id', None)
        brain_hub.get_brain(requested_model, system_prompt)
        # # 2. THE SMART SWAP LOGIC
        # if brain_hub.current_model_id != requested_model and brain_hub.current_model_id is not None:
        #     print(f"{Color.CYAN}[!] Neural Swap Initiated: '{current_model_id}' -> '{requested_model}'{Color.RESET}")
        #     try:
        #        brain_hub.unload_brain()
               
        #     #    brain_hub.current_model_id = requested_model
        #     except Exception as e:
        #         print(f"{Color.RED}Error loading model {requested_model}: {e}{Color.RESET}")
        #         raise HTTPException(status_code=500, detail=f"Failed to load model {requested_model}")
        # else:
        #     print(f"{Color.GREEN}[ * ] Neural Link Persistent: '{requested_model}' is already active.{Color.RESET}")

        # 3. PROCEED TO INFERENCE
        formatted_messages = [{"role": m.role, "content": m.content} for m in request.messages]
        
        # --- NEW STREAMING LOGIC ---
        if request.stream:
            async def event_generator():
                try:
                    # Assuming .chat returns an iterator when stream=True
                    raw_output = brain_hub.orchestrator.llm.chat(formatted_messages, stream=True)
                    func.log("Streaming response initiated...")
                    for chunk in raw_output:
                        if chunk:
                            # Format as Server-Sent Event (SSE)
                            payload = {"choices": [{"delta": {"content": str(chunk)}}]}
                            yield f"data: {json.dumps(payload)}\n\n"
                    # Tell the client we are done
                    func.log("Streaming response completed.")
                    yield "data: [DONE]\n\n"

                except Exception as e:
                    print(f"{Color.RED}Streaming Error: {e}{Color.RESET}")
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
            return StreamingResponse(event_generator(), media_type="text/event-stream")
        
        # --- FALLBACK FOR NON-STREAMING (Standard JSON) ---
        else:
            try:
                raw_output = brain_hub.orchestrator.llm.chat(formatted_messages, stream=False)
                # If stream=False returns an iterator, join it. If it returns a string, just use it.
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