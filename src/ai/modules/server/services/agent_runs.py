"""
Agent runs over HTTP: the same pipelines, tasks and tools as ``ai --agent``, driven by a web client.

One run at a time: it shares the server's loaded model. A run is a background thread that
runs ``AgentOrchestrator.run_loop``; its events go to an append-only log (each with a ``seq``)
that any number of SSE streams read and replay. Closing a stream never stops the run: only a
cancel does. The log of the last run is kept until the next run starts. Tools on the HIL list
wait for the client's decision (``answer_permission``) and are denied after
``PERMISSION_TIMEOUT`` seconds, so nothing gated runs unattended.
"""

import os
import re
import threading
import time
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
    Sends orchestrator events to a run's log and waits for permission answers from HTTP.
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
        waiter = {"event": threading.Event(), "decision": PERMISSION_NO, "tool": tool, "needs_totp": needs_totp,
                  "params": _jsonable(params)}
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
    """State of one run: its event log, pending permissions and orchestrator."""

    def __init__(self, session_id: str, totp_tools: Optional[set] = None, pipeline: str = "default",
                 cwd: str = "", model: Optional[str] = None, prompt: str = ""):
        self.run_id = uuid.uuid4().hex[:12]
        self.pipeline = pipeline
        self.started = time.time()
        self.totp_tools = totp_tools or set()
        self.session_id = session_id
        self.cwd, self.model, self.prompt = cwd, model, prompt
        self.events: List[dict] = []  # append-only; events[i]["seq"] == i + 1
        self.closed = False  # no more events (set after the final ``done``)
        self._cond = threading.Condition()
        self.pending: Dict[str, dict] = {}
        self.orchestrator = None
        self.finished = threading.Event()
        self.finished_at: Optional[float] = None
        self.reason: Optional[str] = None

    def needs_totp(self, tool: str) -> bool:
        return tool in self.totp_tools

    @property
    def last_seq(self) -> int:
        return len(self.events)

    def put(self, event: Optional[dict]) -> None:
        """Appends an event with the next ``seq``; ``None`` closes the log."""
        with self._cond:
            if event is None:
                self.closed = True
            else:
                event = dict(event, seq=len(self.events) + 1)
                if event.get("type") == "done":
                    self.reason = event.get("reason")
                self.events.append(event)
            self._cond.notify_all()

    def events_after(self, after: int, timeout: float) -> tuple:
        """
        Events with ``seq > after``, waiting up to ``timeout`` seconds for one.

        Returns:
            ``(events, closed)``; ``closed`` means the log is complete and every event was returned.
        """
        after = max(0, int(after or 0))
        with self._cond:
            if len(self.events) <= after and not self.closed:
                self._cond.wait(timeout)
            return self.events[after:], self.closed

    def cancel(self) -> None:
        if self.orchestrator is not None:
            self.orchestrator.cancel()
        for request_id, waiter in list(self.pending.items()):  # unblock a tool waiting for approval
            waiter["decision"] = PERMISSION_NO
            waiter["event"].set()
            self.put({"type": "permission_answered", "request_id": request_id,
                      "data": {"decision": "no", "cancelled": True}})


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
                if not filename.endswith(".json") or filename.startswith("."):
                    continue  # editor swap and backup files
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

    def workspace_root(self) -> str:
        """
        The default folder for runs: SERVER_AGENT_WORKDIR, else ``<system>/workspace`` (beside
        models/ and system-prompt/). Created if missing.
        """
        root = (self.config.get(ProgramSetting.SERVER_AGENT_WORKDIR) if self.config else None) \
            or os.path.join(DirectoryManager().get_system_dir(), "workspace")
        root = os.path.realpath(os.path.expanduser(root))
        os.makedirs(root, exist_ok=True)
        return root

    def _workspace_path(self, relative: Optional[str]) -> str:
        root = self.workspace_root()
        path = _inside(root, (relative or "").strip().rstrip("/") or ".")
        if path is None:
            raise AgentApiError(400, f"Path must stay inside the agent workspace ({root}).")
        return path

    def list_workspace(self, relative: Optional[str]) -> dict:
        """Entries of a workspace folder: folders first, then files, each sorted by name."""
        path = self._workspace_path(relative)
        if not os.path.isdir(path):
            raise AgentApiError(404, f"Folder '{relative or '.'}' not found.")
        entries = _scan(path, hidden=False, follow_links=False)  # a link could point outside the workspace
        root = self.workspace_root()
        rel = os.path.relpath(path, root)
        return {"path": "" if rel == "." else rel.replace(os.sep, "/"), "entries": entries}

    def make_workspace_dir(self, relative: str) -> str:
        if not (relative or "").strip().rstrip("/"):
            raise AgentApiError(400, "Send the folder path to create.")
        path = self._workspace_path(relative)
        if os.path.exists(path):
            raise AgentApiError(409, f"'{relative}' already exists.")
        os.makedirs(path)
        return os.path.relpath(path, self.workspace_root()).replace(os.sep, "/")

    # --- any folder ----------------------------------------------------------------------

    def resolve_cwd(self, cwd: Optional[str], must_exist: bool = True) -> str:
        """
        The real path of a run folder. An absolute ``cwd`` is any folder on this machine except
        the refused ones (see ``refused_reason``); a relative or empty one is inside the default
        workspace (older clients) and is created when missing.

        Raises:
            AgentApiError: 400 relative path leaving the workspace, not a directory, or refused.
        """
        cwd = os.path.expanduser((cwd or "").strip())
        if not os.path.isabs(cwd):
            path = _inside(self.workspace_root(), cwd.rstrip("/") or ".")
            if path is None:
                raise AgentApiError(400, "A relative cwd must stay inside the default workspace.")
            if must_exist:
                os.makedirs(path, exist_ok=True)
            return path
        path = os.path.realpath(cwd)
        reason = self.refused_reason(path)
        if reason:
            raise AgentApiError(400, reason)
        if must_exist and not os.path.isdir(path):
            raise AgentApiError(400, f"'{path}' is not an existing directory.")
        return path

    def refused_reason(self, path: str) -> Optional[str]:
        """
        Why ``path`` (a real path) can't be a run folder, or None. Refused: the filesystem root,
        system folders, and the server's own data folders (paired devices, TOTP secret, logs,
        sessions) except the default workspace inside them.
        """
        if os.path.dirname(path) == path:  # "/" or a Windows drive root ("C:\\")
            return "The filesystem root can't be an agent folder."
        if any(_under(path, d) for d in _system_folders()):
            return f"'{path}' is a system folder."
        if _under(path, self.workspace_root()):
            return None
        directory = DirectoryManager()
        for data in (directory.get_system_dir(), directory.get_user_directory()):
            data = os.path.realpath(data)
            if _under(path, data):
                return f"'{path}' is inside the server's data folder ({data})."
        return None

    def list_folder(self, path: str, hidden: bool = False) -> dict:
        """
        Entries of any folder: ``{path, parent, entries:[{name, type, modified, size?}]}``,
        folders first. Raises 400 not absolute or not a directory, 404 missing, 403 unreadable.
        """
        path = os.path.expanduser((path or "").strip())
        if not path or not os.path.isabs(path):
            raise AgentApiError(400, "path must be absolute.")
        path = os.path.realpath(path)
        if not os.path.exists(path):
            raise AgentApiError(404, f"'{path}' not found.")
        if not os.path.isdir(path):
            raise AgentApiError(400, f"'{path}' is not a directory.")
        try:
            entries = _scan(path, hidden=hidden, follow_links=True)
        except PermissionError:
            raise AgentApiError(403, f"'{path}' can't be read.")
        parent = os.path.dirname(path)
        return {"path": path, "parent": None if parent == path else parent, "entries": entries}

    def make_folder(self, path: str) -> str:
        """Creates ``path`` (absolute, parents included). 400 bad or refused, 409 exists, 403 denied."""
        path = os.path.expanduser((path or "").strip())
        if not path or not os.path.isabs(path):
            raise AgentApiError(400, "path must be absolute.")
        path = os.path.realpath(path)
        if os.path.exists(path):
            raise AgentApiError(409, f"'{path}' already exists.")
        reason = self.refused_reason(path)
        if reason:
            raise AgentApiError(400, reason)
        try:
            os.makedirs(path)
        except PermissionError:
            raise AgentApiError(403, f"No permission to create '{path}'.")
        return path

    @staticmethod
    def recent_folders(limit: int = 20) -> List[dict]:
        """Existing folders with saved agent sessions, newest first: ``[{path, updated_at}]``."""
        from ai.agents.session_manager import AgentSessionManager
        root = AgentSessionManager._get_agents_storage_root()
        found: Dict[str, float] = {}
        for project in AgentSessionManager.list_all_projects():
            path = project.get("working_directory")
            if not path or not os.path.isdir(path):
                continue
            folder = os.path.join(root, project["hash"])
            try:
                times = [e.stat().st_mtime for e in os.scandir(folder)
                         if e.name.endswith(".json") and e.name != AgentSessionManager.MANIFEST_FILE]
            except OSError:
                continue
            if times:
                found[path] = max(max(times), found.get(path, 0))
        recent = sorted(found.items(), key=lambda item: item[1], reverse=True)[:limit]
        return [{"path": path, "updated_at": updated} for path, updated in recent]

    def workspace_info(self) -> dict:
        root = self.workspace_root()
        return {"default": root, "home": os.path.expanduser("~"), "recent": self.recent_folders(),
                "sep": os.sep, "roots": _filesystem_roots(),
                # older clients: cwd relative to root
                "root": root, "default_cwd": ""}

    # --- sessions -----------------------------------------------------------------------

    def _session_dir(self, cwd: Optional[str]) -> str:
        """The run folder for ``cwd`` (not created): sessions are stored per working directory."""
        return self.resolve_cwd(cwd, must_exist=False)

    def list_sessions(self, cwd: Optional[str] = None) -> List[Dict[str, Any]]:
        """Saved agent sessions of runs in ``cwd``, newest first (pass one as a run's ``session_id``)."""
        from ai.agents.session_manager import AgentSessionManager
        return AgentSessionManager.list_sessions_detailed(self._session_dir(cwd))

    def read_session(self, session_id: str, cwd: Optional[str] = None) -> Dict[str, Any]:
        """
        The visible conversation of a saved session: ``{session_id, transcript}``, where each
        entry is ``{role: user|agent, agent, text}``, oldest first.

        Raises:
            AgentApiError: 400 bad id or cwd, 404 no such session in ``cwd``.
        """
        from ai.agents.session_manager import AgentSessionManager
        if not re.fullmatch(r"[A-Za-z0-9._-]+", session_id or "") or session_id.startswith("."):
            raise AgentApiError(400, "Invalid session id.")
        folder = self._session_dir(cwd)
        # Checked first: building a manager creates its storage folder.
        if session_id not in {s["session_id"] for s in AgentSessionManager.list_sessions_detailed(folder)}:
            raise AgentApiError(404, f"Session '{session_id}' not found.")
        state = AgentSessionManager(session_id, working_directory=folder).get_session()
        return {"session_id": session_id,
                "transcript": AgentSessionManager.extract_transcript(state, limit=0)}

    def workdir(self, cwd: Optional[str]) -> str:
        """The folder a run works in (see ``resolve_cwd``)."""
        return self.resolve_cwd(cwd)

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

            run = AgentRun(session_id or str(uuid.uuid4()), totp_tools=self.totp_tools(), pipeline=pipeline,
                           cwd=workdir, model=self.brain_hub.current_model_id, prompt=prompt or "")
            prog = SimpleNamespace(llm=self.brain_hub.orchestrator.llm, modules=self.modules)
            try:
                run.orchestrator = build_orchestrator(prog, f"{pipeline}.json", io=WebAgentIO(run))
            except ValueError as e:
                raise AgentApiError(400, str(e))
            run.orchestrator.llm_connector.on_token = lambda token: run.put({"type": "token", "text": str(token)})
            run.put({"type": "run", "run_id": run.run_id, "session_id": run.session_id})
            self.current = run  # replaces the previous run, whose log expires here
            self.brain_hub.agent_running = True

        threading.Thread(target=self._run, args=(run, text, workdir), daemon=True,
                         name=f"agent-run-{run.run_id}").start()
        return run

    def _run(self, run: AgentRun, text: str, workdir: str) -> None:
        import ai.tools.base as tool_base

        previous, previous_root = os.getcwd(), tool_base.PROJECT_ROOT
        try:
            # Tools resolve @ROOT and relative paths from PROJECT_ROOT, which is fixed when the
            # module is imported (the server's own folder); agent sessions use the cwd. Point
            # both at the workdir so every file a run touches stays inside it.
            tool_base.PROJECT_ROOT = workdir
            os.chdir(workdir)
            result = run.orchestrator.run_loop(user_prompt=text, session_id=run.session_id)
            run.put({"type": "done", "reason": getattr(result, "reason", "error"),
                     "message": getattr(result, "message", "")})
        except Exception as e:
            func.error(f"Agent API: run {run.run_id} failed: {e}")
            run.put({"type": "error", "agent": None, "text": str(e), "data": {}})
            run.put({"type": "done", "reason": "error", "message": str(e)})
        finally:
            tool_base.PROJECT_ROOT = previous_root
            os.chdir(previous)
            try:
                run.orchestrator.close()
            except Exception as e:
                func.debug(f"Agent API: close failed: {e}")
            self.brain_hub.agent_running = False
            run.finished_at = time.time()
            run.finished.set()
            run.put(None)

    def get(self, run_id: str) -> AgentRun:
        if self.current is None or self.current.run_id != run_id:
            raise AgentApiError(404, f"Run '{run_id}' not found.")
        return self.current

    def totp_tools(self) -> set:
        """
        Tools whose approval needs an authenticator code. Empty unless SERVER_TOTP_ENABLED is
        true and a secret exists (off by default in the first release).
        """
        enabled = self.config.get(ProgramSetting.SERVER_TOTP_ENABLED) if self.config else False
        if enabled is not True or self.totp is None or not self.totp.enabled:
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
        # So every viewer (not only the one that answered) closes the request.
        run.put({"type": "permission_answered", "request_id": request_id, "data": {"decision": decision}})

    def current_info(self) -> dict:
        """
        The run in progress, or ``{"active": false, "last": {...}}`` with the last finished run
        (``last`` is null when there was none since the server started).
        """
        run = self.current
        if not self.busy:
            last = None
            if run is not None:
                last = {"run_id": run.run_id, "session_id": run.session_id, "cwd": run.cwd,
                        "pipeline": run.pipeline, "started": run.started, "finished": run.finished_at,
                        "reason": run.reason, "last_seq": run.last_seq}
            return {"active": False, "last": last}
        return {"active": True, "run_id": run.run_id, "session_id": run.session_id, "pipeline": run.pipeline,
                "started": run.started, "cwd": run.cwd, "model": run.model, "prompt": run.prompt,
                "last_seq": run.last_seq,
                "pending_permissions": [{"request_id": rid, "tool": w.get("tool"), "params": w.get("params"),
                                         "needs_totp": w.get("needs_totp", False)}
                                        for rid, w in list(run.pending.items())]}

    def cancel(self, run_id: str) -> None:
        self.get(run_id).cancel()

    def cancel_current(self) -> None:
        if self.busy:
            self.current.cancel()


_WINDOWS_HIDDEN = 0x2 | 0x4  # FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM


def _under(path: str, folder: str) -> bool:
    """``path`` is ``folder`` or inside it (case-insensitive on Windows)."""
    path, folder = os.path.normcase(path), os.path.normcase(folder).rstrip("\\/")
    return path == folder or path.startswith(folder + os.sep)


def _filesystem_roots() -> List[str]:
    """Where browsing starts: ``["/"]``, or the existing drives on Windows (``["C:\\", "D:\\"]``)."""
    if os.name != "nt":
        return [os.sep]
    import string
    return [f"{letter}:\\" for letter in string.ascii_uppercase if os.path.isdir(f"{letter}:\\")]


def _system_folders() -> List[str]:
    """Folders a run may not use (nor anything under them)."""
    if os.name == "nt":
        env = os.environ.get
        return [os.path.realpath(p) for p in (
            env("SystemRoot", r"C:\Windows"), env("ProgramFiles", r"C:\Program Files"),
            env("ProgramFiles(x86)", r"C:\Program Files (x86)"), env("ProgramData", r"C:\ProgramData"))]
    names = ("/bin", "/boot", "/dev", "/etc", "/lib", "/lib32", "/lib64", "/proc", "/root", "/run",
             "/sbin", "/sys", "/usr", "/var", "/System", "/Library", "/private")
    return sorted({os.path.realpath(p) for p in names})


def _scan(path: str, hidden: bool, follow_links: bool) -> List[dict]:
    """Folder entries ``{name, type, modified, size?}``, folders first, each sorted by name."""
    entries = []
    with os.scandir(path) as it:
        for entry in it:
            if entry.name.startswith(".") and not hidden:
                continue
            if entry.is_symlink() and not follow_links:
                continue
            try:
                info = entry.stat(follow_symlinks=follow_links)
                kind = "dir" if entry.is_dir(follow_symlinks=follow_links) else "file"
            except OSError:
                continue  # broken link, vanished file
            if not hidden and getattr(info, "st_file_attributes", 0) & _WINDOWS_HIDDEN:
                continue  # Windows hides by attribute, not by a leading dot
            item = {"name": entry.name, "type": kind, "modified": info.st_mtime}
            if kind == "file":
                item["size"] = info.st_size
            entries.append(item)
    entries.sort(key=lambda e: (e["type"] != "dir", e["name"].lower()))
    return entries


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
