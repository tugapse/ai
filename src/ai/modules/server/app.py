import json
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from config import ProgramConfig
from .brain_hub import BrainHub
from .schemas import ChatRequest

app = FastAPI(title="JARVIS Neural Server")
config = ProgramConfig.load()
hub = BrainHub(config)

@app.get("/status")
async def get_status():
    return {
        "status": "online",
        "active_model": hub.current_model_id,
        "token_stats": hub.get_stats()
    }

@app.get("/models")
async def list_models():
    """Lists available model configs on the Main PC."""
    return {"models": hub.list_available_models()}

@app.post("/v1/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        # Get the requested brain (swaps weights if model_id changed)
        llm = hub.get_brain(request.model_id, request.system_prompt)
        
        async def token_generator():
            # llm.chat returns a generator
            for token in llm.chat(
                messages=request.messages,
                stream=True,
                options=request.options or hub.orchestrator.get_params()
            ):
                # Send token + live stats
                yield json.dumps({
                    "token": token,
                    "stats": hub.get_stats()
                }) + "\n"

        return StreamingResponse(token_generator(), media_type="application/x-ndjson")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/unload")
async def unload_model():
    """Manually free up the GPU."""
    hub.unload_brain()
    return {"message": "GPU memory cleared."}

@app.post("/v1/shutdown")
async def emergency_stop():
    """Stops current generation immediately."""
    if hub.orchestrator.llm:
        hub.orchestrator.llm.request_shutdown()
    return {"message": "Generation stopped."}