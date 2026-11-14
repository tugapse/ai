"""
Background knowledge builds for the server API (one at a time).

A build uses the loaded model, so it claims it like an agent run does (brain_hub.agent_running)
and refuses to start while an agent run is active; agent runs refuse to start while a build runs.
"""

import threading
import time
import uuid
from typing import Any, Dict, List, Optional

import ai.functions as func

MAX_EVENTS = 200


class KnowledgeBuildJob:
    def __init__(self, project: str, params: Dict[str, Any]):
        self.job_id = uuid.uuid4().hex[:12]
        self.project = project
        self.params = params
        self.state = "running"          # running | done | failed | cancelled
        self.events: List[Dict[str, Any]] = []
        self.report: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.started_at = time.time()
        self.finished_at: Optional[float] = None
        self.cancel_event = threading.Event()

    def progress(self, event: Dict[str, Any]) -> None:
        self.events.append({**event, "at": time.time()})
        del self.events[:-MAX_EVENTS]

    def info(self) -> Dict[str, Any]:
        last = self.events[-1] if self.events else None
        return {"job_id": self.job_id, "state": self.state, "project": self.project, "params": self.params,
                "started_at": self.started_at, "finished_at": self.finished_at, "last_event": last,
                "events": self.events[-20:], "report": self.report, "error": self.error}


class KnowledgeBuildService:
    def __init__(self, brain_hub: Any, agent_service: Any, knowledge_module: Any):
        self.brain_hub = brain_hub
        self.agent_service = agent_service
        self.module = knowledge_module
        self.current: Optional[KnowledgeBuildJob] = None
        self.jobs: Dict[str, KnowledgeBuildJob] = {}
        self._lock = threading.Lock()

    @property
    def busy(self) -> bool:
        return self.current is not None and self.current.state == "running"

    def status(self, project: str) -> Dict[str, Any]:
        return self.module.get_instance().service.status(project)

    def start(self, project: str, **params) -> KnowledgeBuildJob:
        from ai.modules.server.services.agent_runs import AgentApiError
        with self._lock:
            if self.busy:
                raise AgentApiError(409, "A knowledge build is already running.")
            if self.agent_service is not None and self.agent_service.busy:
                raise AgentApiError(409, "An agent run is in progress; try again when it ends.")
            with self.brain_hub._lock:
                if self.brain_hub.orchestrator.llm is None:
                    raise AgentApiError(409, "No model loaded.")
                self.brain_hub.agent_running = True
                self.brain_hub.knowledge_building = True
            job = KnowledgeBuildJob(project, {k: v for k, v in params.items() if v is not None})
            self.current = job
            self.jobs[job.job_id] = job
        threading.Thread(target=self._run, args=(job, params), daemon=True, name=f"kb-build-{job.job_id}").start()
        return job

    def _run(self, job: KnowledgeBuildJob, params: Dict[str, Any]) -> None:
        try:
            service = self.module.get_instance().service
            job.report = service.build(job.project, llm=self.brain_hub.orchestrator.llm,
                                       on_progress=job.progress, cancel_event=job.cancel_event, **params)
            job.state = "cancelled" if job.report.get("cancelled") else "done"
        except Exception as e:
            func.error(f"Knowledge build {job.job_id} failed: {e}")
            job.state, job.error = "failed", str(e)
        finally:
            job.finished_at = time.time()
            self.brain_hub.agent_running = False
            self.brain_hub.knowledge_building = False

    def get(self, job_id: str) -> KnowledgeBuildJob:
        from ai.modules.server.services.agent_runs import AgentApiError
        job = self.jobs.get(job_id)
        if job is None:
            raise AgentApiError(404, f"Unknown build '{job_id}'.")
        return job

    def cancel(self, job_id: str) -> None:
        self.get(job_id).cancel_event.set()
