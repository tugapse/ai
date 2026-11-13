from fastapi import APIRouter, Depends, HTTPException, Request

from ai.modules.server.routers.auth import require_device
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

    :param request: The FastAPI Request object.
    :param session_folder: Optional path to filter sessions by sub-folder.
    :raises HTTPException: If the session manager is not configured (500) or if loading fails (500).
    :return: A dictionary containing the list of sessions.
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
    """
    Retrieve the content of a specific saved session identified by its path.

    :param request: The FastAPI Request object.
    :param session_path: The full path to the session file.
    :raises HTTPException: If the session is not found (404), the path is invalid (400), or if loading fails (500).
    :return: The content of the session.
    """
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

# The /title route is declared first: the catch-all {session_path:path} would swallow it.
@router.put("/api/v1/sessions/{session_path:path}/title", dependencies=[Depends(require_device)])
async def update_session_title(
    request: Request, session_path: str, payload: UpdateSessionRequest
):
    """
    Update only the session title for a specified session path.

    :param request: The FastAPI Request object.
    :param session_path: The path of the session to update.
    :param payload: The request body containing the new session title.
    :raises HTTPException: If the session manager is not configured (500), title is missing (400), or if the update fails (404, 400, 500).
    :return: The result returned by the session manager upon successful title update.
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

@router.put("/api/v1/sessions/{session_path:path}", dependencies=[Depends(require_device)])
async def update_session_content(
    request: Request, session_path: str, payload: UpdateSessionRequest
):
    """
    Overwrite the entire session content for a specified session path.

    Expects payload.session_content to be provided.

    :param request: The FastAPI Request object.
    :param session_path: The path of the session to update.
    :param payload: The request body containing the new session content.
    :raises HTTPException: If the session manager is not configured (500), content is missing (400), or if the update fails (404, 400, 500).
    :return: A success message upon successful update.
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

    if isinstance(content, list):
        content = [m.model_dump() if hasattr(m, "model_dump") else m for m in content]
        if not all(isinstance(m, dict) and "role" in m and "content" in m for m in content):
            raise HTTPException(status_code=400, detail="Each message needs 'role' and 'content'.")
    elif not isinstance(content, dict) or not isinstance(content.get("messages"), list):
        raise HTTPException(
            status_code=400,
            detail="session_content must be a session object with a 'messages' list, or a list of messages.")
    elif payload.session_title is not None:
        content = {**content, "session_title": payload.session_title}

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

@router.delete("/api/v1/sessions/{session_path:path}", dependencies=[Depends(require_device)])
async def delete_session(request: Request, session_path: str):
    """
    Delete a specific session file identified by its path.

    :param request: The FastAPI Request object.
    :param session_path: The path of the session to delete.
    :raises HTTPException: If the session manager is not configured (500), the session is not found (404), the path is invalid (400), or if deletion fails (500).
    :return: A success status message upon successful deletion.
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