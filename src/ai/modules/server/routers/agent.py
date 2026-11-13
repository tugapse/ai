"""
/api/v1/agent/*: run agent pipelines (tasks, tools) from a web client.

Every route needs a paired device (see routers/auth.py). See services/agent_runs.py.
"""

import asyncio
import json
from typing import Any, Optional

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


class PipelineContent(BaseModel):
    content: Any


class PipelineCreate(BaseModel):
    name: str
    content: Any


def _pipeline_call(fn, *args):
    from ai.modules.server.services.pipelines import PipelineError
    try:
        return fn(*args)
    except PipelineError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)


def _tools(request: Request) -> list:
    from ai.agents.agent_orchestrator import get_hil_tools
    from ai.modules.server.services import pipelines
    service = _service(request)
    return pipelines.list_tools(service.modules, get_hil_tools(), service.totp_tools())


@router.get("/tools")
async def tools(request: Request):
    """Tools a pipeline agent can use: ``[{name, description, needs_permission, needs_totp}]``."""
    return await asyncio.to_thread(_tools, request)


@router.get("/pipelines/{name}")
async def pipeline(name: str, request: Request):
    """A pipeline file: ``{name, source: user|system, content}``."""
    from ai.modules.server.services import pipelines
    _service(request)
    return _pipeline_call(pipelines.read, name)


@router.put("/pipelines/{name}")
async def save_pipeline(name: str, payload: PipelineContent, request: Request):
    """
    Validates and overwrites a pipeline in the folder it came from: ``{name, source, warnings}``.
    400 ``detail`` is a list of problems; ``warnings`` lists tools no active module provides.
    """
    from ai.modules.server.services import pipelines
    known = {t["name"] for t in await asyncio.to_thread(_tools, request)}
    result = _pipeline_call(pipelines.save, name, payload.content, known)
    _audit(request, "pipeline_save", name=name, source=result["source"])
    return result


@router.post("/pipelines", status_code=201)
async def create_pipeline(payload: PipelineCreate, request: Request):
    """Validates and creates a pipeline in the user folder (409 if the name exists)."""
    from ai.modules.server.services import pipelines
    known = {t["name"] for t in await asyncio.to_thread(_tools, request)}
    result = _pipeline_call(pipelines.create, payload.name, payload.content, known)
    _audit(request, "pipeline_create", name=payload.name)
    return result


@router.delete("/pipelines/{name}")
async def delete_pipeline(name: str, request: Request):
    """Deletes a pipeline (not ``default``; 409 while a run uses it)."""
    from ai.modules.server.services import pipelines
    service = _service(request)
    if service.busy and service.current.pipeline == name:
        raise HTTPException(status_code=409, detail=f"Pipeline '{name}' is used by the current run.")
    result = _pipeline_call(pipelines.delete, name)
    _audit(request, "pipeline_delete", name=name, source=result["source"])
    return result


@router.get("/tasks")
async def tasks(request: Request):
    """Task templates (user task folder); a run's ``task`` takes one of these names."""
    return _service(request).list_tasks()


@router.get("/tasks/{name:path}")
async def task(name: str, request: Request):
    service = _service(request)
    return {"name": name, "content": _call(service.read_task, name)}


@router.get("/sessions")
async def sessions(request: Request, cwd: Optional[str] = None):
    """Saved sessions of runs in ``cwd`` (relative to the workspace), newest first:
    ``[{session_id, user_request, last_user_message, updated_at, turns, iteration}]``."""
    return _call(_service(request).list_sessions, cwd)


@router.get("/sessions/{session_id}")
async def session(session_id: str, request: Request, cwd: Optional[str] = None):
    """A saved session's conversation: ``{session_id, transcript: [{role, agent, text}]}``."""
    return _call(_service(request).read_session, session_id, cwd)


class MkdirRequest(BaseModel):
    path: str


@router.get("/workspace")
async def workspace(request: Request):
    """
    Where runs can work: ``{default, home, recent:[{path, updated_at}], root, default_cwd}``.
    A run's ``cwd`` is any absolute folder (``recent`` = folders with saved sessions, newest
    first), or a path relative to ``default`` (``root`` and ``default_cwd`` are for older clients).
    """
    return _service(request).workspace_info()


@router.get("/fs/list")
async def fs_list(request: Request, path: str, hidden: bool = False):
    """Any folder's entries: ``{path, parent, entries:[{name, type, modified, size?}]}``, folders first."""
    return _call(_service(request).list_folder, path, hidden)


@router.post("/fs/mkdir", status_code=201)
async def fs_mkdir(payload: MkdirRequest, request: Request):
    """Creates an absolute folder (and missing parents)."""
    created = _call(_service(request).make_folder, payload.path)
    _audit(request, "fs_mkdir", path=created)
    return {"path": created}


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
    Starts a run and streams its events as SSE (first ``run`` with run_id and session_id) until
    a ``done`` event and ``[DONE]``. Every event has a ``seq``. Closing the stream does not stop
    the run: reattach with ``GET /runs/{run_id}/events?after=<seq>``, stop it with ``/cancel``.
    """
    service = _service(request)
    run = await asyncio.to_thread(
        _call, service.start, payload.prompt, payload.pipeline, payload.task,
        payload.model, payload.session_id, payload.cwd)
    _audit(request, "agent_run", run_id=run.run_id, session_id=run.session_id,
           pipeline=payload.pipeline or "default", task=payload.task, model=payload.model, cwd=payload.cwd)

    return StreamingResponse(_stream(run, 0), media_type="text/event-stream")


@router.get("/runs/{run_id}/events")
async def run_events(run_id: str, request: Request, after: int = 0):
    """
    Replays a run's events with ``seq > after``, then streams new ones until ``done`` and
    ``[DONE]`` (a finished run replays and closes). Any number of viewers; disconnecting never
    cancels. 404 for an unknown run or one replaced by a newer run.
    """
    run = _call(_service(request).get, run_id)
    return StreamingResponse(_stream(run, after), media_type="text/event-stream")


async def _stream(run, after: int):
    """SSE of ``run``'s log from ``after``; a comment every HEARTBEAT_SECONDS keeps proxies open."""
    idle = 0.0
    while True:
        events, closed = await asyncio.to_thread(run.events_after, after, 0.5)
        for event in events:
            yield _sse(event)
        if events:
            after, idle = events[-1]["seq"], 0.0
        if closed:
            break
        if not events:
            idle += 0.5
            if idle >= HEARTBEAT_SECONDS:
                idle = 0.0
                yield ": ping\n\n"
    yield "data: [DONE]\n\n"


@router.get("/runs/current")
async def current_run(request: Request):
    """
    The run in progress, so a client that lost its stream can reattach, show it and cancel it:
    ``{"active": true, run_id, session_id, pipeline, started, cwd, model, prompt, last_seq,
    pending_permissions:[...]}``, or ``{"active": false, "last": {run_id, session_id, cwd,
    pipeline, started, finished, reason, last_seq} | null}``.
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
