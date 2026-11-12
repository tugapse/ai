"""
Agent runs over HTTP: the same pipelines, tasks and tools as ``ai --agent``, driven by a web client.

One run at a time: it shares the server's loaded model. A run is a background thread that
runs ``AgentOrchestrator.run_loop``; its events go to a queue the SSE response drains. Tools on
the HIL list wait for the client's decision (``answer_permission``) and are denied after
``PERMISSION_TIMEOUT`` seconds.
"""

import os
import queue
import re
import threading
import uuid
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

import ai.functions as func
from ai.agents.agent_io import (AgentEvent, AgentIO, PERMISSION_ALWAYS, PERMISSION_NO,
                                PERMISSION_YES)
from ai.config import ProgramSetting
from ai.services.directory_manager import DirectoryManager

PERMISSION_TIMEOUT = 600
DEFAULT_TOTP_TOOLS = ["execute_command", "delete_file"]
_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_DECISIONS = {"yes": PERMISSION_YES, "no": PERMISSION_NO, "always": PERMISSION_ALWAYS}


class AgentApiError(Exception):
    """An agent request the server refuses; ``status`` is the HTTP code to answer."""

    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status, self.detail = status, detail


class WebAgentIO(AgentIO):
    """
    Sends orchestrator events to a run's queue and waits for permission answers from HTTP.
    A question to the user ends the turn (``awaiting_user``); the answer comes as a new run.
    """
    blocking_user_input = False

    def __init__(self, run: "AgentRun"):
        self.run = run

    def emit(self, event: AgentEvent) -> None:
        self.run.put({"type": getattr(event.type, "value", str(event.type)), "agent": event.agent,
                      "text": event.text, "data": _jsonable(event.data)})

    def request_permission(self, tool: str, params: Dict[str, Any]) -> str:
        from ai.agents.tool_preview import describe_tool_request

        request_id = uuid.uuid4().hex[:12]
        needs_totp = self.run.needs_totp(tool)
        waiter = {"event": threading.Event(), "decision": PERMISSION_NO, "tool": tool, "needs_totp": needs_totp}
        self.run.pending[request_id] = waiter
        self.run.put({"type": "permission", "request_id": request_id, "tool": tool,
                      "params": _jsonable(params), "needs_totp": needs_totp,
                      "preview": [_ANSI.sub("", line) for line in describe_tool_request(tool, params)]})
        answered = waiter["event"].wait(PERMISSION_TIMEOUT)
        self.run.pending.pop(request_id, None)
        if not answered:
            self.run.put({"type": "info", "agent": None, "text": f"Permission for {tool} timed out: denied.",
                          "data": {"request_id": request_id}})
        return waiter["decision"]


class AgentRun:
    """State of one run: its events, pending permissions and orchestrator."""

    def __init__(self, session_id: str, totp_tools: Optional[set] = None):
        self.run_id = uuid.uuid4().hex[:12]
        self.totp_tools = totp_tools or set()
        self.session_id = session_id
        self.events: "queue.Queue[Optional[dict]]" = queue.Queue()
        self.pending: Dict[str, dict] = {}
        self.orchestrator = None
        self.finished = threading.Event()

    def needs_totp(self, tool: str) -> bool:
        return tool in self.totp_tools

    def put(self, event: Optional[dict]) -> None:
        self.events.put(event)

    def cancel(self) -> None:
        if self.orchestrator is not None:
            self.orchestrator.cancel()
        for waiter in list(self.pending.values()):  # unblock a tool waiting for approval
            waiter["decision"] = PERMISSION_NO
            waiter["event"].set()


class AgentRunService:
    """Starts, tracks and controls web agent runs."""

    def __init__(self, brain_hub, config, modules=None, totp=None):
        self.brain_hub = brain_hub
        self.config = config
        self.modules = modules
        self.totp = totp  # TotpGuard; when enabled, approving TOTP tools needs a code
        self.current: Optional[AgentRun] = None
        self._lock = threading.Lock()

    @property
    def busy(self) -> bool:
        return self.current is not None and not self.current.finished.is_set()

    # --- catalogue --------------------------------------------------------------------

    @staticmethod
    def list_pipelines() -> List[dict]:
        """Pipelines in the user and system folders (user wins), with their agents and tools."""
        import json

        directory = DirectoryManager()
        found: Dict[str, dict] = {}
        for folder in (directory.get_system_pipelines_directory(), directory.get_user_pipelines_directory()):
            if not os.path.isdir(folder):
                continue
            for filename in sorted(os.listdir(folder)):
                if not filename.endswith(".json"):
                    continue
                try:
                    with open(os.path.join(folder, filename), encoding="utf-8") as f:
                        data = json.load(f)
                except Exception as e:
                    func.log(f"Agent API: skipping pipeline {filename}: {e}", level="WARN")
                    continue
                found[filename[:-5]] = {
                    "name": filename[:-5],
                    "title": data.get("name", filename[:-5]),
                    "description": data.get("description", ""),
                    "entry_point": data.get("entry_point"),
                    "agents": [{"name": name, "tools": agent.get("tools", [])}
                               for name, agent in (data.get("agents") or {}).items()],
                }
        return [found[k] for k in sorted(found)]

    @staticmethod
    def tasks_directory() -> str:
        return os.path.join(DirectoryManager().get_user_directory(), "task")

    @classmethod
    def list_tasks(cls) -> List[dict]:
        """Task templates (``.md``) under the user task folder; names keep their subfolder."""
        root = cls.tasks_directory()
        tasks = []
        if os.path.isdir(root):
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
                for filename in sorted(filenames):
                    if filename.endswith(".md"):
                        rel = os.path.relpath(os.path.join(dirpath, filename), root)
                        tasks.append({"name": rel[:-3].replace(os.sep, "/")})
        return tasks

    @classmethod
    def read_task(cls, name: str) -> str:
        path = _inside(cls.tasks_directory(), f"{name.removesuffix('.md')}.md")
        if path is None or not os.path.isfile(path):
            raise AgentApiError(404, f"Task '{name}' not found.")
        with open(path, encoding="utf-8") as f:
            return f.read()

    def workdir(self, cwd: Optional[str]) -> str:
        """The folder a run works in: ``cwd`` inside SERVER_AGENT_WORKDIR (created if missing)."""
        root = (self.config.get(ProgramSetting.SERVER_AGENT_WORKDIR) if self.config else None) \
            or os.path.join(DirectoryManager().get_user_directory(), "..", "workspace")
        root = os.path.realpath(os.path.expanduser(root))
        os.makedirs(root, exist_ok=True)
        path = _inside(root, cwd or ".")
        if path is None:
            raise AgentApiError(400, f"cwd must stay inside the agent workdir ({root}).")
        os.makedirs(path, exist_ok=True)
        return path

    # --- runs -------------------------------------------------------------------------

    def start(self, prompt: str, pipeline: Optional[str] = None, task: Optional[str] = None,
              model: Optional[str] = None, session_id: Optional[str] = None,
              cwd: Optional[str] = None) -> AgentRun:
        """
        Validates the request, loads the model and starts the run thread.

        Raises:
            AgentApiError: 400 bad input, 404 unknown task/pipeline/model, 409 busy or no model.
        """
        from ai.agents.agent import build_orchestrator
        from ai.modules.server.exceptions import ModelLoadError, ModelNotFoundError

        text = "\n\n".join(part for part in (self.read_task(task) if task else "", prompt or "") if part.strip())
        if not text.strip():
            raise AgentApiError(400, "Send a prompt or a task.")
        pipeline = (pipeline or "default").removesuffix(".json")
        if pipeline not in {p["name"] for p in self.list_pipelines()}:
            raise AgentApiError(404, f"Pipeline '{pipeline}' not found.")
        workdir = self.workdir(cwd)

        with self._lock:
            if self.busy:
                raise AgentApiError(409, "An agent run is already in progress.")
            if model:
                try:
                    self.brain_hub.get_brain(model, "")
                except ModelNotFoundError as e:
                    raise AgentApiError(404, str(e))
                except ModelLoadError as e:
                    raise AgentApiError(500, str(e))
            if self.brain_hub.orchestrator.llm is None:
                raise AgentApiError(409, "No model loaded; pass model.")

            run = AgentRun(session_id or str(uuid.uuid4()), totp_tools=self.totp_tools())
            prog = SimpleNamespace(llm=self.brain_hub.orchestrator.llm, modules=self.modules)
            try:
                run.orchestrator = build_orchestrator(prog, f"{pipeline}.json", io=WebAgentIO(run))
            except ValueError as e:
                raise AgentApiError(400, str(e))
            run.orchestrator.llm_connector.on_token = lambda token: run.put({"type": "token", "text": str(token)})
            self.current = run
            self.brain_hub.agent_running = True

        threading.Thread(target=self._run, args=(run, text, workdir), daemon=True,
                         name=f"agent-run-{run.run_id}").start()
        return run

    def _run(self, run: AgentRun, text: str, workdir: str) -> None:
        previous = os.getcwd()
        try:
            # Tools and agent sessions resolve paths from the working directory.
            os.chdir(workdir)
            result = run.orchestrator.run_loop(user_prompt=text, session_id=run.session_id)
            run.put({"type": "done", "reason": getattr(result, "reason", "error"),
                     "message": getattr(result, "message", "")})
        except Exception as e:
            func.log(f"Agent API: run {run.run_id} failed: {e}", level="ERROR")
            run.put({"type": "error", "agent": None, "text": str(e), "data": {}})
            run.put({"type": "done", "reason": "error", "message": str(e)})
        finally:
            os.chdir(previous)
            try:
                run.orchestrator.close()
            except Exception as e:
                func.debug(f"Agent API: close failed: {e}")
            self.brain_hub.agent_running = False
            run.finished.set()
            run.put(None)

    def get(self, run_id: str) -> AgentRun:
        if self.current is None or self.current.run_id != run_id:
            raise AgentApiError(404, f"Run '{run_id}' not found.")
        return self.current

    def totp_tools(self) -> set:
        """Tools whose approval needs an authenticator code; empty while TOTP is not set up."""
        if self.totp is None or not self.totp.enabled:
            return set()
        tools = self.config.get(ProgramSetting.SERVER_TOTP_TOOLS) if self.config else None
        return set(tools if isinstance(tools, list) else DEFAULT_TOTP_TOOLS)

    def answer_permission(self, run_id: str, request_id: str, decision: str, totp: Optional[str] = None) -> None:
        """
        Resolves a permission request. For a TOTP tool, yes needs a valid code and always counts
        as yes (a standing approval would skip the code next time). A wrong code is 401 and the
        request stays open.
        """
        run = self.get(run_id)
        waiter = run.pending.get(request_id)
        if waiter is None:
            raise AgentApiError(404, f"Permission request '{request_id}' not found.")
        if decision not in _DECISIONS:
            raise AgentApiError(400, "decision must be yes, no or always.")
        if waiter.get("needs_totp") and decision != "no":
            if not totp:
                raise AgentApiError(401, "This tool needs an authenticator code (totp).")
            if not self.totp.verify(totp):
                raise AgentApiError(401, "Wrong or already used authenticator code.")
            decision = "yes"
        waiter["decision"] = _DECISIONS[decision]
        waiter["event"].set()

    def cancel(self, run_id: str) -> None:
        self.get(run_id).cancel()

    def cancel_current(self) -> None:
        if self.busy:
            self.current.cancel()


def _inside(root: str, relative: str) -> Optional[str]:
    """``root/relative`` resolved, or None when it leaves ``root``."""
    if os.path.isabs(relative) or ".." in relative.replace("\\", "/").split("/"):
        return None
    root = os.path.realpath(root)
    path = os.path.realpath(os.path.join(root, relative))
    return path if path == root or path.startswith(root + os.sep) else None


def _jsonable(value: Any) -> Any:
    """Event data made JSON-safe (tool results can hold any object)."""
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    return str(value)
