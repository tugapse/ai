"""
/api/v1/agent/*: run agent pipelines (tasks, tools) from a web client.

Every route needs a paired device (see routers/auth.py). See services/agent_runs.py.
"""

import asyncio
import json
import queue
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ai.modules.server.routers.auth import require_device
from ai.modules.server.services.agent_runs import AgentApiError, AgentRunService

router = APIRouter(prefix="/api/v1/agent", dependencies=[Depends(require_device)])
HEARTBEAT_SECONDS = 5


class AgentRunRequest(BaseModel):
    prompt: str = ""
    pipeline: Optional[str] = None
    task: Optional[str] = None
    model: Optional[str] = None
    session_id: Optional[str] = None
    cwd: Optional[str] = None


class PermissionAnswer(BaseModel):
    request_id: str
    decision: str  # yes | no | always
    totp: Optional[str] = None  # authenticator code, for events with needs_totp


def _service(request: Request) -> AgentRunService:
    service: Optional[AgentRunService] = getattr(request.app.state, "agent_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="Agent API not configured.")
    return service


def _audit(request: Request, event: str, **data) -> None:
    auth = getattr(request.app.state, "auth", None)
    device = getattr(request.state, "device", None) or {}
    if auth is not None:
        auth.audit(event, device_id=device.get("device_id"), **data)


def _call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except AgentApiError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)


@router.get("/pipelines")
async def pipelines(request: Request):
    """Pipelines a run may use: name, title, description, entry point, agents and their tools."""
    return _service(request).list_pipelines()


@router.get("/tasks")
async def tasks(request: Request):
    """Task templates (user task folder); a run's ``task`` takes one of these names."""
    return _service(request).list_tasks()


@router.get("/tasks/{name:path}")
async def task(name: str, request: Request):
    service = _service(request)
    return {"name": name, "content": _call(service.read_task, name)}


class MkdirRequest(BaseModel):
    path: str


@router.get("/workspace")
async def workspace(request: Request):
    """The folder agent runs work in; a run's ``cwd`` is relative to ``root``."""
    return {"root": _service(request).workspace_root(), "default_cwd": ""}


@router.get("/workspace/list")
async def workspace_list(request: Request, path: str = ""):
    """Folders and files under ``path`` (relative to the workspace root), folders first."""
    return _call(_service(request).list_workspace, path)


@router.post("/workspace/mkdir", status_code=201)
async def workspace_mkdir(payload: MkdirRequest, request: Request):
    """Creates a folder (and missing parents) inside the workspace."""
    created = _call(_service(request).make_workspace_dir, payload.path)
    _audit(request, "workspace_mkdir", path=created)
    return {"path": created}


@router.post("/runs")
async def start_run(payload: AgentRunRequest, request: Request):
    """
    Starts a run and streams its events as SSE until a ``done`` event and ``[DONE]``.
    Closing the stream cancels the run (an agent never runs unattended).
    """
    service = _service(request)
    run = await asyncio.to_thread(
        _call, service.start, payload.prompt, payload.pipeline, payload.task,
        payload.model, payload.session_id, payload.cwd)
    _audit(request, "agent_run", run_id=run.run_id, session_id=run.session_id,
           pipeline=payload.pipeline or "default", task=payload.task, model=payload.model, cwd=payload.cwd)

    async def events():
        finished = False
        try:
            yield _sse({"type": "run", "run_id": run.run_id, "session_id": run.session_id})
            idle = 0.0
            while True:
                try:
                    event = await asyncio.to_thread(run.events.get, True, 0.5)
                except queue.Empty:
                    idle += 0.5
                    if idle >= HEARTBEAT_SECONDS:
                        # A model step can take minutes with no event; writing a comment is how
                        # a dropped client is noticed (and its run cancelled).
                        idle = 0.0
                        yield ": ping\n\n"
                    continue
                idle = 0.0
                if event is None:
                    finished = True
                    break
                yield _sse(event)
            yield "data: [DONE]\n\n"
        finally:
            if not finished:
                run.cancel()

    return StreamingResponse(events(), media_type="text/event-stream")


@router.get("/runs/current")
async def current_run(request: Request):
    """
    The run in progress, so a client that lost its stream can show it and cancel it:
    ``{"active": true, run_id, session_id, pipeline, started, pending_permissions:[...]}``
    or ``{"active": false}``.
    """
    return _service(request).current_info()


@router.post("/runs/{run_id}/permission")
async def permission(run_id: str, payload: PermissionAnswer, request: Request):
    """Answers a ``permission`` event: decision yes, no or always (always = for the rest of the run)."""
    service = _service(request)
    try:
        service.answer_permission(run_id, payload.request_id, payload.decision, payload.totp)
    except AgentApiError as e:
        auth = getattr(request.app.state, "auth", None)
        if e.status == 401 and auth is not None:
            # Wrong codes count towards the per-IP rate limit, like failed logins.
            auth.fail(request.client.host if request.client else "", 401, e.detail, kind="totp")
        raise HTTPException(status_code=e.status, detail=e.detail)
    _audit(request, "agent_permission", run_id=run_id, request_id=payload.request_id, decision=payload.decision,
           totp=bool(payload.totp) or None)
    return {"status": "ok"}


@router.post("/runs/{run_id}/cancel")
async def cancel(run_id: str, request: Request):
    """Stops the run at the next safe point; the stream then ends with ``done`` / ``cancelled``."""
    service = _service(request)
    _call(service.cancel, run_id)
    _audit(request, "agent_cancel", run_id=run_id)
    return {"status": "cancelling"}


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
