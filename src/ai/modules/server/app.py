from pathlib import Path
import json
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import Any, Dict, Optional

import ai.functions as func  # reuse your logging utilities

from ai.modules.server.schemas import (
    ChatCompletionRequest,
    UpdateSessionRequest,
    PromptCreateRequest,
    PromptUpdateRequest,
)
from ai.modules.server.middleware import MIMETypeFixerMiddleware
from ai.modules.server.services.session_manager import (
    InvalidPathError as SessionInvalidPathError,
    SessionManager,
    SessionNotFoundError,
)
from ai.modules.server.services.prompt_manager import (
    InvalidPathError as PromptInvalidPathError,
    PromptManager,
    PromptNotFoundError,
    PromptAccessError,
)
from ai.modules.server.services.chat import ChatService
from ai.modules.server.brain_hub import BrainHub


def create_app(brain_hub: BrainHub, config: Dict[str, Any]) -> FastAPI:
    """
    Build and configure the FastAPI app, wiring dependencies into app.state.
    """
    SESSION_ROOT_DIR = Path(func.get_root_directory()) / "sessions" / "server"
    PROMPT_ROOT_DIR = Path(func.get_root_directory()) / "system"

    app = FastAPI(title="JARVIS Neural Hub")

    # Include external routers
    from ai.modules.server.routers.sessions import router as sessions_router
    from ai.modules.server.routers.prompts import router as prompts_router

    app.include_router(sessions_router)
    app.include_router(prompts_router)

    session_manager = SessionManager(SESSION_ROOT_DIR)
    app.state.session_manager = session_manager
    prompt_manager = PromptManager(PROMPT_ROOT_DIR)
    app.state.prompt_manager = prompt_manager
    chat_service = ChatService(brain_hub, SESSION_ROOT_DIR, config)
    app.state.chat_service = chat_service

    @app.post("/api/v1/chat/completions")
    @app.post("/api/v1/chat")
    async def chat_completions(request: Request, payload: ChatCompletionRequest):
        """
        Handle chat completions (streaming and non-streaming).
        Delegates to ChatService via app.state.chat_service.
        """
        if chat_service is None:
            raise HTTPException(status_code=500, detail="Chat service not configured.")

        func.debug(
            f"Incoming chat request: model={payload.model!r}, system_prompt={payload.system_prompt!r}, "
            f"stream={payload.stream}, session_folder={payload.session_folder!r}, "
            f"session_id={payload.session_id!r}"
        )

        return await chat_service.chat_completion(payload)

    @app.get("/api/health")
    async def health(request: Request):
        model_name = (
            getattr(brain_hub.get_stats(), "model_chat_name", "JARVIS")
            if brain_hub
            else "JARVIS"
        )
        return {"status": "online", "model": model_name}

    func.log("Initializing FastAPI app with wired dependencies...")



    FRONTEND_BUILD_DIR = Path(__file__).resolve().parent / "frontend"
    if FRONTEND_BUILD_DIR.is_dir():
        app.mount("/", StaticFiles(directory=FRONTEND_BUILD_DIR, html=True), name="static_app")
        func.debug(f"Static files mounted from {FRONTEND_BUILD_DIR} to root \'/\'.")
    
    app.add_middleware(MIMETypeFixerMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app