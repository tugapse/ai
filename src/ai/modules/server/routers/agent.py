"""
/api/v1/agent/*: run agent pipelines (tasks, tools) from a web client.

Every route needs ``Authorization: Bearer <SERVER_AGENT_TOKEN>``. See services/agent_runs.py.
"""

import asyncio
import json
import queue
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ai.modules.server.services.agent_runs import AgentApiError, AgentRunService

router = APIRouter(prefix="/api/v1/agent")


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


def _service(request: Request, authorization: Optional[str]) -> AgentRunService:
    service: Optional[AgentRunService] = getattr(request.app.state, "agent_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail="Agent API not configured.")
    try:
        service.check_token(authorization)
    except AgentApiError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)
    return service


def _call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except AgentApiError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)


@router.get("/pipelines")
async def pipelines(request: Request, authorization: Optional[str] = Header(None)):
    """Pipelines a run may use: name, title, description, entry point, agents and their tools."""
    return _service(request, authorization).list_pipelines()


@router.get("/tasks")
async def tasks(request: Request, authorization: Optional[str] = Header(None)):
    """Task templates (user task folder); a run's ``task`` takes one of these names."""
    return _service(request, authorization).list_tasks()


@router.get("/tasks/{name:path}")
async def task(name: str, request: Request, authorization: Optional[str] = Header(None)):
    service = _service(request, authorization)
    return {"name": name, "content": _call(service.read_task, name)}


@router.post("/runs")
async def start_run(payload: AgentRunRequest, request: Request, authorization: Optional[str] = Header(None)):
    """
    Starts a run and streams its events as SSE until a ``done`` event and ``[DONE]``.
    Closing the stream cancels the run (an agent never runs unattended).
    """
    service = _service(request, authorization)
    run = await asyncio.to_thread(
        _call, service.start, payload.prompt, payload.pipeline, payload.task,
        payload.model, payload.session_id, payload.cwd)

    async def events():
        finished = False
        try:
            yield _sse({"type": "run", "run_id": run.run_id, "session_id": run.session_id})
            while True:
                try:
                    event = await asyncio.to_thread(run.events.get, True, 0.5)
                except queue.Empty:
                    continue
                if event is None:
                    finished = True
                    break
                yield _sse(event)
            yield "data: [DONE]\n\n"
        finally:
            if not finished:
                run.cancel()

    return StreamingResponse(events(), media_type="text/event-stream")


@router.post("/runs/{run_id}/permission")
async def permission(run_id: str, payload: PermissionAnswer, request: Request,
                     authorization: Optional[str] = Header(None)):
    """Answers a ``permission`` event: decision yes, no or always (always = for the rest of the run)."""
    service = _service(request, authorization)
    _call(service.answer_permission, run_id, payload.request_id, payload.decision)
    return {"status": "ok"}


@router.post("/runs/{run_id}/cancel")
async def cancel(run_id: str, request: Request, authorization: Optional[str] = Header(None)):
    """Stops the run at the next safe point; the stream then ends with ``done`` / ``cancelled``."""
    service = _service(request, authorization)
    _call(service.cancel, run_id)
    return {"status": "cancelling"}


def _sse(event: dict) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
