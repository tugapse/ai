from fastapi import APIRouter, HTTPException, Request
from typing import Optional

from ai.modules.server.schemas import UpdateSessionRequest
from ai.modules.server.services.session_manager import (
    InvalidPathError as SessionInvalidPathError,
    SessionNotFoundError,
)

router = APIRouter()

@router.get("/api/v1/sessions")
async def get_sessions(request: Request, session_folder: Optional[str] = None):
    """
    Retrieve a list of saved sessions. Optionally filter by a sub-folder.
    """
    session_manager = request.app.state.session_manager
    if session_manager is None:
        raise HTTPException(
            status_code=500, detail="Session manager not configured."
        )
    try:
        sessions = session_manager.list_sessions(session_folder)
        return {"sessions": sessions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load sessions: {e}")

@router.get("/api/v1/sessions/{session_path:path}")
async def get_session_content(request: Request, session_path: str):
    session_manager = request.app.state.session_manager
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

@router.put("/api/v1/sessions/{session_path:path}")
async def update_session_content(
    request: Request, session_path: str, payload: UpdateSessionRequest
):
    """
    Overwrite the entire session content.
    Expects payload.session_content to be provided.
    """
    session_manager = request.app.state.session_manager
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

@router.put("/api/v1/sessions/{session_path:path}/title")
async def update_session_title(
    request: Request, session_path: str, payload: UpdateSessionRequest
):
    """
    Update only the session title.
    """
    session_manager = request.app.state.session_manager
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

@router.delete("/api/v1/sessions/{session_path:path}")
async def delete_session(request: Request, session_path: str):
    """
    Delete a specific session file.
    """
    session_manager = request.app.state.session_manager
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
