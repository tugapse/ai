"""
/api/v1/knowledge/*: feed and inspect the agents' knowledge base (component JSON + Markdown docs).

Every route needs a paired device (see routers/auth.py). In relay mode the knowledge lives
here, next to the agents; only inference goes to the Brain Server.
"""

import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ai.modules.server.routers.auth import require_device

router = APIRouter(prefix="/api/v1/knowledge", dependencies=[Depends(require_device)])


class BuildRequest(BaseModel):
    cwd: Optional[str] = None                # project folder (absolute, or relative to the agent workspace)
    mode: Optional[str] = "changed"          # missing | changed | all | diff[:branch]
    files: Optional[List[str]] = None
    only: Optional[str] = None               # docs | knowledge
    source_root: Optional[str] = None
    extensions: Optional[List[str]] = None   # None: the last build's, config, or every text file; ["all"]: every text file
    max_files: Optional[int] = None
    force: bool = False


class SourceRequest(BaseModel):
    id: Optional[str] = None
    path: Optional[str] = None                     # folder/file on this machine
    kind: Optional[str] = "auto"                   # auto | knowledge | docs
    documents: Optional[List[Dict[str, Any]]] = None  # component JSON objects or {"path", "content"} Markdown


def _module(request: Request):
    modules = getattr(request.app.state, "modules", None)
    try:
        module = modules["knowledge"] if modules is not None else None
    except (KeyError, TypeError):
        module = None
    if module is None:
        raise HTTPException(status_code=503, detail="Knowledge module disabled (KNOWLEDGE_ENABLED).")
    return module


def _base_dir(request: Request) -> str:
    config = getattr(request.app.state, "config", None) or {}
    workdir = config.get("SERVER_AGENT_WORKDIR") if isinstance(config, dict) else None
    return os.path.expanduser(workdir) if workdir else os.getcwd()


@router.get("/sources")
def list_sources(request: Request):
    """Loaded sources with their component/doc counts."""
    return {"sources": _module(request).get_instance().list_sources()}


@router.post("/sources", status_code=201)
def add_source(request: Request, body: SourceRequest):
    """
    Adds a source: ``{"path": ...}`` loads a folder on this machine (relative to the agent
    workdir); ``{"id": ..., "documents": [...]}`` ingests documents sent in the request.
    """
    module = _module(request)
    store = module.get_instance()
    if body.documents is not None:
        if not body.id:
            raise HTTPException(status_code=400, detail="'id' is required with 'documents'.")
        summary = store.ingest_documents(body.id, body.documents)
        return {"status": "SUCCESS", **summary}
    if not body.path:
        raise HTTPException(status_code=400, detail="Send 'path' or 'documents'.")

    from ai.modules.knowledge.sources import parse_source_entry
    spec = parse_source_entry({"id": body.id, "path": body.path, "kind": body.kind}, base_dir=_base_dir(request))
    if spec is None:
        raise HTTPException(status_code=400, detail="Invalid source.")
    try:
        summary = store.add_source(spec, reload=True)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"status": "SUCCESS", **summary}


@router.delete("/sources/{source_id}")
def remove_source(request: Request, source_id: str):
    if not _module(request).get_instance().remove_source(source_id):
        raise HTTPException(status_code=404, detail=f"Unknown source '{source_id}'.")
    return {"status": "SUCCESS"}


@router.get("/search")
def search(request: Request, q: str, top_k: int = 5, source: Optional[List[str]] = None):
    """Hybrid search over the knowledge base (what agents get from search_knowledge)."""
    store = _module(request).get_instance()
    return {"query": q, "results": store.search(q, top_k=max(1, min(top_k, 25)), sources=source or None)}


@router.get("/component")
def component(request: Request, path: str):
    card = _module(request).get_instance().get_component(path)
    if not card:
        raise HTTPException(status_code=404, detail=f"'{path}' is not in the knowledge base.")
    return card


# --- building ---------------------------------------------------------------------------

def _builds(request: Request):
    builds = getattr(request.app.state, "knowledge_builds", None)
    if builds is None:
        module = _module(request)
        from ai.modules.server.services.knowledge_builds import KnowledgeBuildService
        builds = KnowledgeBuildService(request.app.state.brain_hub, getattr(request.app.state, "agent_service", None), module)
        request.app.state.knowledge_builds = builds
    return builds


def _project(request: Request, cwd: Optional[str]) -> str:
    from ai.modules.server.services.agent_runs import AgentApiError
    agents = getattr(request.app.state, "agent_service", None)
    try:
        return agents.resolve_cwd(cwd) if agents is not None else os.path.abspath(cwd or _base_dir(request))
    except AgentApiError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)


@router.get("/status")
def build_status(request: Request, cwd: Optional[str] = None):
    """Coverage of a project's generated knowledge (docs + component JSON)."""
    return _builds(request).status(_project(request, cwd))


@router.post("/build", status_code=202)
def start_build(request: Request, body: BuildRequest):
    """Starts a background build of a project's knowledge with the loaded model."""
    from ai.modules.server.services.agent_runs import AgentApiError
    project = _project(request, body.cwd)
    try:
        job = _builds(request).start(project, mode=body.mode or "changed", files=body.files,
                                     kinds=[body.only] if body.only else None, source_root=body.source_root,
                                     extensions=body.extensions, max_files=body.max_files, force=body.force)
    except AgentApiError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)
    return job.info()


@router.get("/build/{job_id}")
def get_build(request: Request, job_id: str):
    from ai.modules.server.services.agent_runs import AgentApiError
    try:
        return _builds(request).get(job_id).info()
    except AgentApiError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)


@router.post("/build/{job_id}/cancel")
def cancel_build(request: Request, job_id: str):
    from ai.modules.server.services.agent_runs import AgentApiError
    try:
        _builds(request).cancel(job_id)
    except AgentApiError as e:
        raise HTTPException(status_code=e.status, detail=e.detail)
    return {"status": "SUCCESS"}
