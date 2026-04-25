from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import Any, Dict, Optional
import functions as func  # reuse your logging utilities

from .schemas import (
    ChatCompletionRequest,
    UpdateSessionRequest,
    PromptCreateRequest,
    PromptUpdateRequest,
)
from .middleware import MIMETypeFixerMiddleware
from .services.session_manager import (
    InvalidPathError as SessionInvalidPathError,
    SessionManager,
    SessionNotFoundError,
)
from .services.prompt_manager import (
    InvalidPathError as PromptInvalidPathError,
    PromptManager,
    PromptNotFoundError,
    PromptAccessError,
)
from .services.chat import ChatService
from .brain_hub import BrainHub


def create_app(brain_hub: BrainHub, config: Dict[str, Any]) -> FastAPI:
    """
    Build and configure the FastAPI app, wiring dependencies into app.state.
    """
    SESSION_ROOT_DIR = Path(func.get_root_directory()) / "sessions" / "server"
    PROMPT_ROOT_DIR = Path(func.get_root_directory()) / "system"

    app = FastAPI(title="JARVIS Neural Hub")
    session_manager = SessionManager(SESSION_ROOT_DIR)
    prompt_manager = PromptManager(PROMPT_ROOT_DIR)
    chat_service = ChatService(brain_hub, SESSION_ROOT_DIR, config)

    @app.get("/api/v1/sessions")
    async def get_sessions(request: Request, session_folder: Optional[str] = None):
        """
        Retrieve a list of saved sessions. Optionally filter by a sub-folder.
        """
        if session_manager is None:
            raise HTTPException(
                status_code=500, detail="Session manager not configured."
            )
        try:
            sessions = session_manager.list_sessions(session_folder)
            return {"sessions": sessions}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to load sessions: {e}")

    @app.get("/api/v1/sessions/{session_path:path}")
    async def get_session_content(request: Request, session_path: str):
        if session_manager is None:
            raise HTTPException(
                status_code=500, detail="Session manager not configured."
            )
        try:
            return session_manager.load_session(session_path)
        except SessionNotFoundError:
            raise HTTPException(status_code=404, detail="Session not found")
        except SessionInvalidPathError:
            raise HTTPException(status_code=400, detail="Invalid path")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to load session: {e}")

    @app.put("/api/v1/sessions/{session_path:path}")
    async def update_session_content(
        request: Request, session_path: str, payload: UpdateSessionRequest
    ):
        """
        Overwrite the entire session content.
        Expects payload.session_content to be provided.
        """
        if session_manager is None:
            raise HTTPException(
                status_code=500, detail="Session manager not configured."
            )

        content = getattr(payload, "session_content", None)
        if content is None:
            raise HTTPException(
                status_code=400, detail="Missing session_content in request."
            )

        try:
            session_manager.update_session_content(session_path, content)
            return {"message": "Session content updated successfully"}
        except SessionNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except SessionInvalidPathError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to update session: {e}"
            )

    @app.put("/api/v1/sessions/{session_path:path}/title")
    async def update_session_title(
        request: Request, session_path: str, payload: UpdateSessionRequest
    ):
        """
        Update only the session title.
        """
        if session_manager is None:
            raise HTTPException(
                status_code=500, detail="Session manager not configured."
            )

        title = getattr(payload, "session_title", None)
        if title is None:
            raise HTTPException(
                status_code=400, detail="Missing session_title in request."
            )

        try:
            result = session_manager.update_session_title(session_path, title)
            return result
        except SessionNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except SessionInvalidPathError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to update session title: {e}"
            )

    @app.delete("/api/v1/sessions/{session_path:path}")
    async def delete_session(request: Request, session_path: str):
        """
        Delete a specific session file.
        """
        if session_manager is None:
            raise HTTPException(
                status_code=500, detail="Session manager not configured."
            )

        try:
            session_manager.delete_session(session_path)
            return {"status": "success", "message": f"Session {session_path} deleted."}
        except SessionNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except SessionInvalidPathError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to delete session: {e}"
            )

    # --- Prompt Management Endpoints ---

    @app.get("/api/v1/prompts")
    async def get_prompts(request: Request, prompt_folder: Optional[str] = None):
        """
        Retrieve a list of saved prompts. Optionally filter by a sub-folder.
        """
        if prompt_manager is None:
            raise HTTPException(
                status_code=500, detail="Prompt manager not configured."
            )
        try:
            prompts = prompt_manager.list_prompts(prompt_folder)
            return {"prompts": prompts}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to load prompts: {e}")

    @app.get("/api/v1/prompts/{prompt_path:path}")
    async def get_prompt_content(request: Request, prompt_path: str):
        """
        Get the content of a specific prompt file.
        """
        if prompt_manager is None:
            raise HTTPException(
                status_code=500, detail="Prompt manager not configured."
            )
        try:
            return prompt_manager.read_prompt(prompt_path)
        except PromptNotFoundError:
            raise HTTPException(status_code=404, detail="Prompt not found")
        except PromptInvalidPathError:
            raise HTTPException(status_code=400, detail="Invalid prompt path")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to load prompt: {e}")

    @app.post("/api/v1/prompts")
    async def create_prompt(request: Request, payload: PromptCreateRequest):
        """
        Create a new prompt file.
        """
        if prompt_manager is None:
            raise HTTPException(
                status_code=500, detail="Prompt manager not configured."
            )
        try:
            result = prompt_manager.create_prompt(
                payload.prompt_path, payload.content
            )
            return result
        except PromptInvalidPathError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except PromptAccessError as e:
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create prompt: {e}")

    @app.put("/api/v1/prompts/{prompt_path:path}")
    async def update_prompt_content(
        request: Request, prompt_path: str, payload: PromptUpdateRequest
    ):
        """
        Update/overwrite an existing prompt file.
        """
        if prompt_manager is None:
            raise HTTPException(
                status_code=500, detail="Prompt manager not configured."
            )
        try:
            result = prompt_manager.update_prompt(prompt_path, payload.content)
            return result
        except PromptNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except PromptInvalidPathError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except PromptAccessError as e:
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to update prompt: {e}")

    @app.delete("/api/v1/prompts/{prompt_path:path}")
    async def delete_prompt(request: Request, prompt_path: str):
        """
        Delete a specific prompt file.
        """
        if prompt_manager is None:
            raise HTTPException(
                status_code=500, detail="Prompt manager not configured."
            )
        try:
            prompt_manager.delete_prompt(prompt_path)
            return {"status": "success", "message": f"Prompt {prompt_path} deleted."}
        except PromptNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except PromptInvalidPathError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except PromptAccessError as e:
            raise HTTPException(status_code=500, detail=str(e))
        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Failed to delete prompt: {e}"
            )


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