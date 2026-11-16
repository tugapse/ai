"""
KnowledgeBuilder: generates a project's knowledge with the loaded LLM, one call per source file.

Python port of the `ai-create-code-documentation` / `ai-extract-knowledge` shell engine:
- docs: Markdown per source file (task `code/create-code-documentation`);
- knowledge: component JSON per source file (task `code/extract-knowledge`), with the file's
  doc as extra context when it exists.

Outputs mirror the source tree under <output>/docs and <output>/knowledge. A `.state.json` per
kind keeps the source sha and status of every file, so `changed` mode needs no git and failed
files are retried. The manifest ([source -> target] lines) is sent inline, filtered to the files
the source refers to (the shell engine only sent its path, which a direct call cannot read).
"""

import hashlib
import json
import os
import re
import subprocess
import tempfile
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

import ai.functions as func
from ai.modules.knowledge.registry import KnowledgeRegistry, project_key, project_slug
from ai.modules.knowledge.schema import looks_like_component, parse_component
from ai.modules.knowledge.sources import SourceSpec

KINDS = ("docs", "knowledge")
TASKS = {
    "docs": ("code/create-code-documentation", ".md"),
    "knowledge": ("code/extract-knowledge", ".json"),
}
MODES = ("missing", "changed", "all", "diff", "files")
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".mypy_cache", ".pytest_cache"}
STATE_FILE = ".state.json"
ALL_EXTENSIONS = ("all", "*")   # --ext all / *: every text file (an empty extension list)
MAX_FILE_BYTES = 256 * 1024     # all-files mode: bigger files are skipped (generated, data, dumps)
IGNORED_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "pipfile.lock", "uv.lock",
    "cargo.lock", "composer.lock", "gemfile.lock", "go.sum", "packages.lock.json", ".ds_store",
}
IGNORED_SUFFIXES = (".min.js", ".min.css", ".map", ".lock", ".log", ".pyc", ".pyo", ".tsbuildinfo")
BINARY_EXTENSIONS = {
    "png", "jpg", "jpeg", "gif", "bmp", "ico", "webp", "avif", "tif", "tiff", "psd", "blend", "fbx", "glb",
    "pdf", "zip", "gz", "tgz", "bz2", "xz", "7z", "rar", "jar", "war", "whl", "egg",
    "so", "dll", "dylib", "exe", "bin", "o", "a", "lib", "class", "wasm", "pyd",
    "mp3", "wav", "ogg", "flac", "mp4", "mkv", "mov", "avi", "webm",
    "ttf", "otf", "woff", "woff2", "eot", "db", "sqlite", "sqlite3", "db-shm", "db-wal",
    "gguf", "safetensors", "pt", "pth", "onnx", "npy", "npz", "pkl", "parquet",
}
CHARS_PER_TOKEN = 3.2
DOC_SEPARATOR = "\n\n# --- END OF DOCUMENTATION CONTEXT --- #\n\n"

LLMCall = Callable[[List[Dict[str, str]], str], str]  # (messages, system_prompt) -> text


# --------------------------------------------------------------------------- config

@dataclass
class BuildConfig:
    project: str
    source_root: str                 # absolute
    extensions: List[str]            # empty: every text file
    output_dir: str                  # absolute: <output>/docs and <output>/knowledge
    kinds: Tuple[str, ...] = KINDS
    # Sources whose output keeps the full file name (foo.ts -> foo.ts.md) because another source
    # has the same name without extension (foo.html). Filled by KnowledgeBuilder.scan().
    full_name_targets: set = field(default_factory=set)

    @property
    def all_files(self) -> bool:
        return not self.extensions

    @property
    def extensions_label(self) -> str:
        return ", ".join(self.extensions) if self.extensions else "all text files"

    def kind_dir(self, kind: str) -> str:
        return os.path.join(self.output_dir, kind)

    def target_rel(self, kind: str, rel: str) -> str:
        base = rel if rel in self.full_name_targets else os.path.splitext(rel)[0]
        return base + TASKS[kind][1]

    def target_path(self, kind: str, rel: str) -> str:
        return os.path.join(self.kind_dir(kind), self.target_rel(kind, rel))

    @property
    def name(self) -> str:
        return os.path.basename(self.project.rstrip(os.sep)) or "project"

    def source_specs(self) -> List[SourceSpec]:
        return [SourceSpec(id=f"{self.name}-{kind}", path=self.kind_dir(kind), kind="docs" if kind == "docs" else "knowledge")
                for kind in KINDS]


def _norm_exts(exts: Iterable[str]) -> List[str]:
    out = []
    for e in exts or []:
        for part in str(e).split(","):
            part = part.strip().lstrip(".").lower()
            if part and part not in out:
                out.append(part)
    return out


def _resolve_exts(value: Any) -> Optional[List[str]]:
    """Extension list from a setting; [] = all files ('all' or '*'), None = not set."""
    if value is None:
        return None
    exts = _norm_exts([value] if isinstance(value, str) else value)
    return [] if any(e in ALL_EXTENSIONS for e in exts) else exts


def resolve_build_config(project: str, registry: Optional[KnowledgeRegistry] = None, config: Any = None,
                         source_root: Optional[str] = None, extensions: Optional[Iterable[str]] = None,
                         output_dir: Optional[str] = None, kinds: Optional[Iterable[str]] = None) -> BuildConfig:
    """
    Build settings for a project: explicit values, then the project's registry entry, then config,
    then defaults (source root 'src' when it exists, every text file, output <root>/knowledge/<slug>).
    Extensions 'all' or '*' (or an empty list) mean every text file.
    """
    project = project_key(project)
    saved = registry.build_config(project) if registry else {}

    def cfg(key, default=None):
        try:
            value = config.get(key, default) if config is not None else default
        except Exception:
            value = default
        return default if value is None else value

    root = source_root or saved.get("source_root")
    if not root:
        root = "src" if os.path.isdir(os.path.join(project, "src")) else "."
    root = root if os.path.isabs(root) else os.path.join(project, root)

    exts = _resolve_exts(extensions) if extensions else None
    if exts is None and "extensions" in saved:
        exts = _resolve_exts(saved.get("extensions"))
    if exts is None:
        exts = _resolve_exts(cfg("KNOWLEDGE_EXTENSIONS") or None)
    exts = exts or []

    out = output_dir or saved.get("output")
    if not out:
        base = cfg("KNOWLEDGE_OUTPUT_DIR") or os.path.join(_root_dir(), "knowledge")
        out = os.path.join(os.path.expanduser(base), project_slug(project))
    out = os.path.abspath(os.path.expanduser(out))

    chosen = tuple(k for k in (kinds or KINDS) if k in KINDS) or KINDS
    return BuildConfig(project=project, source_root=os.path.normpath(os.path.abspath(root)),
                       extensions=exts, output_dir=out, kinds=chosen)


def _root_dir() -> str:
    try:
        return func.get_root_directory()
    except Exception:
        return os.path.expanduser("~/Ai")


# --------------------------------------------------------------------------- llm

def default_llm_call(llm: Any) -> LLMCall:
    """LLM call through ai.direct.ask (same path as `ai --task ... -o file`)."""
    def call(messages: List[Dict[str, str]], system_prompt: str) -> str:
        from ai.direct import ask
        out = os.path.join(tempfile.gettempdir(), f"kb_build_{os.getpid()}_{threading.get_ident()}.md")
        previous = getattr(llm, "system_prompt", None)
        try:
            try:
                llm.system_prompt = system_prompt
            except Exception:
                pass
            if os.path.exists(out):
                os.remove(out)
            ask(llm, messages, write_to_file=True, output_filename=out, hide_think_anim=True,
                print_output=False, stream=True)
            with open(out, "r", encoding="utf-8") as f:
                return f.read()
        finally:
            try:
                llm.system_prompt = previous
            except Exception:
                pass
            if os.path.exists(out):
                os.remove(out)
    return call


def _context_limit(llm: Any) -> Optional[int]:
    """
    Prompt tokens the model can take, or None when unknown. Some backends (gguf) only fill
    token_info_count once the model is loaded and report 2048 before that, so the configured
    context size (n_ctx) is taken into account too.
    """
    if llm is None:
        return None
    candidates = []
    try:
        candidates.append(int(llm.token_info_count.max_context_window or 0))
    except Exception:
        pass
    for attr in ("_n_ctx", "n_ctx"):
        try:
            candidates.append(int(getattr(llm, attr, 0) or 0))
        except (TypeError, ValueError):
            pass
    try:
        candidates.append(int((getattr(llm, "options", None) or {}).get("n_ctx") or 0))
    except Exception:
        pass
    window = max(candidates or [0])
    if window <= 0:
        return None
    try:
        out = int(llm.token_info_count.max_output_tokens or 0)
    except Exception:
        out = 0
    out = min(out, window // 2)  # keep at least half of the window for the prompt
    return window - out


# --------------------------------------------------------------------------- output checks

_FENCE_RE = re.compile(r"^\s*```[a-zA-Z0-9_-]*\s*\n(.*?)\n?```\s*$", re.S)


def clean_output(kind: str, text: str) -> str:
    text = (text or "").strip()
    m = _FENCE_RE.match(text)
    if m:
        text = m.group(1).strip()
    if kind == "knowledge":
        start, end = text.find("{"), text.rfind("}")
        if start > 0 or (end != -1 and end < len(text) - 1):
            if start != -1 and end > start:
                text = text[start:end + 1]
    return text + "\n"


def validate_output(kind: str, text: str) -> Optional[str]:
    """None when valid, else the reason."""
    if not text or not text.strip():
        return "empty output"
    if kind == "knowledge":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            return f"invalid JSON: {e}"
        if not looks_like_component(data):
            return "JSON has no 'component' object"
        try:
            parse_component(data)
        except Exception as e:
            return f"schema: {str(e).splitlines()[0]}"
        return None
    if len(text.split()) < 20:
        return "documentation too short"
    return None


# --------------------------------------------------------------------------- builder

def _sha(path: str) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class _IgnoredPaths(set):
    """Paths from git's ignore list; a path is ignored when it or one of its folders is listed."""

    def __contains__(self, rel: object) -> bool:
        rel = str(rel)
        if set.__contains__(self, rel):
            return True
        parts = rel.split("/")
        return any(set.__contains__(self, "/".join(parts[:i])) for i in range(1, len(parts)))


class KnowledgeBuilder:
    """Generates docs and component knowledge for a project's source files."""

    def __init__(self, config: BuildConfig, llm: Any = None, llm_call: Optional[LLMCall] = None,
                 on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
                 cancel_event: Optional[threading.Event] = None, max_retries: int = 1):
        self.config = config
        self.llm = llm
        self.llm_call = llm_call or (default_llm_call(llm) if llm is not None else None)
        self.on_progress = on_progress or (lambda event: None)
        self.cancel_event = cancel_event or threading.Event()
        self.max_retries = max_retries
        self._states: Dict[str, Dict[str, Any]] = {}

    # ------------------------------------------------------------------ files
    def scan(self) -> List[str]:
        """
        Source files (paths relative to the source root), sorted. With no extensions: every text
        file that git doesn't ignore, skipping hidden files, binaries, lockfiles and files over
        MAX_FILE_BYTES.
        """
        root = self.config.source_root
        output = self.config.output_dir + os.sep
        ignored = self._git_ignored(root) if self.config.all_files else set()
        out = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")
                                 and not (os.path.join(dirpath, d) + os.sep).startswith(output))
            for name in filenames:
                rel = os.path.relpath(os.path.join(dirpath, name), root).replace(os.sep, "/")
                if rel not in ignored and self._wanted(os.path.join(dirpath, name)):
                    out.append(rel)
        out.sort()
        self._mark_name_clashes(out)
        return out

    def _wanted(self, path: str) -> bool:
        name = os.path.basename(path)
        ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
        if not self.config.all_files:
            return ext in self.config.extensions
        lower = name.lower()
        if lower.startswith(".") or lower in IGNORED_FILES or lower.endswith(IGNORED_SUFFIXES) or ext in BINARY_EXTENSIONS:
            return False
        try:
            if os.path.getsize(path) > MAX_FILE_BYTES:
                return False
            with open(path, "rb") as f:
                return b"\0" not in f.read(8192)
        except OSError:
            return False

    @staticmethod
    def _git_ignored(root: str) -> set:
        """Root-relative paths git ignores (empty when root isn't in a git repo)."""
        try:
            out = subprocess.run(["git", "-C", root, "ls-files", "--others", "--ignored", "--exclude-standard",
                                  "--directory", "--no-empty-directory"],
                                 capture_output=True, text=True, timeout=30)
        except Exception:
            return set()
        if out.returncode != 0:
            return set()
        ignored = set()
        for line in out.stdout.splitlines():
            ignored.add(line.rstrip("/"))
        return _IgnoredPaths(ignored)

    def _mark_name_clashes(self, files: List[str]) -> None:
        """Sources sharing a name without extension (foo.ts, foo.html) keep their full name in the output."""
        by_stem: Dict[str, List[str]] = {}
        for rel in files:
            by_stem.setdefault(os.path.splitext(rel)[0], []).append(rel)
        self.config.full_name_targets = {rel for group in by_stem.values() if len(group) > 1 for rel in group}

    def to_rel(self, path: str) -> Optional[str]:
        """Source-root-relative path for a user/agent path (absolute, @ROOT/..., project- or source-relative)."""
        p = str(path).strip().replace("\\", "/")
        if p.startswith("@ROOT"):
            p = os.path.join(self.config.project, p[len("@ROOT"):].lstrip("/"))
        candidates = [p] if os.path.isabs(p) else [os.path.join(self.config.project, p), os.path.join(self.config.source_root, p)]
        for c in candidates:
            c = os.path.normpath(os.path.abspath(c))
            if os.path.isfile(c) and (c + os.sep).startswith(self.config.source_root + os.sep):
                rel = os.path.relpath(c, self.config.source_root).replace(os.sep, "/")
                if self._wanted(c):
                    return rel
        return None

    # ------------------------------------------------------------------ state
    def _state(self, kind: str) -> Dict[str, Any]:
        if kind not in self._states:
            path = os.path.join(self.config.kind_dir(kind), STATE_FILE)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
            data.setdefault("files", {})
            self._states[kind] = data
        return self._states[kind]

    def _save_state(self, kind: str) -> None:
        state = self._state(kind)
        path = os.path.join(self.config.kind_dir(kind), STATE_FILE)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=1, sort_keys=True)
        os.replace(tmp, path)

    def file_status(self, kind: str, rel: str) -> str:
        """ok | missing | outdated | error"""
        target = self.config.target_path(kind, rel)
        entry = self._state(kind)["files"].get(rel) or {}
        if entry.get("status") == "error":
            return "error"
        if not os.path.isfile(target) or os.path.getsize(target) == 0:
            return "missing"
        if not entry.get("sha"):
            return "ok"  # generated before state tracking (e.g. by the shell engine)
        try:
            return "ok" if entry["sha"] == _sha(os.path.join(self.config.source_root, rel)) else "outdated"
        except OSError:
            return "missing"

    # ------------------------------------------------------------------ planning
    def git_changed(self, target: str = "master") -> List[str]:
        try:
            top = subprocess.run(["git", "-C", self.config.source_root, "rev-parse", "--show-toplevel"],
                                 capture_output=True, text=True, check=True).stdout.strip()
            names = subprocess.run(["git", "-C", self.config.source_root, "diff", "--name-only", "--diff-filter=d",
                                    f"{target}..."], capture_output=True, text=True, check=True).stdout.split()
        except Exception as e:
            raise RuntimeError(f"git diff against '{target}' failed: {e}")
        out = []
        for name in names:
            rel = self.to_rel(os.path.join(top, name))
            if rel:
                out.append(rel)
        return out

    def plan(self, mode: str = "changed", files: Optional[Iterable[str]] = None, diff_target: str = "master") -> List[str]:
        """Source files to process for a mode (the kinds are decided per file in run())."""
        mode = (mode or "changed").lower()
        if mode.startswith("diff"):
            if ":" in mode:
                diff_target = mode.split(":", 1)[1] or diff_target
            return self.git_changed(diff_target)
        if files:
            out, seen = [], set()
            for f in files:
                rel = self.to_rel(f)
                if rel and rel not in seen:
                    seen.add(rel)
                    out.append(rel)
            return out
        all_files = self.scan()
        if mode == "all":
            return all_files
        wanted = {"missing": ("missing", "error"), "changed": ("missing", "error", "outdated")}.get(mode)
        if wanted is None:
            raise ValueError(f"Unknown mode '{mode}'. Use one of: missing, changed, all, diff[:branch], or files.")
        return [rel for rel in all_files if any(self.file_status(k, rel) in wanted for k in self.config.kinds)]

    def status(self, limit: int = 20) -> Dict[str, Any]:
        """Coverage of the project's knowledge."""
        files = self.scan()
        out: Dict[str, Any] = {"project": self.config.project, "source_root": self.config.source_root,
                               "extensions": self.config.extensions or ["all"], "output": self.config.output_dir,
                               "source_files": len(files)}
        for kind in KINDS:
            buckets: Dict[str, List[str]] = {"ok": [], "missing": [], "outdated": [], "error": []}
            for rel in files:
                buckets[self.file_status(kind, rel)].append(rel)
            out[kind] = {k: len(v) for k, v in buckets.items()}
            for k in ("missing", "outdated", "error"):
                if buckets[k]:
                    out[kind][f"{k}_files"] = buckets[k][:limit]
        return out

    # ------------------------------------------------------------------ prompt
    def manifest(self, kind: str, files: List[str]) -> List[str]:
        return [f"[{rel} -> {self.config.target_rel(kind, rel)}]" for rel in files]

    @staticmethod
    def related_files(rel: str, source: str, files: List[str]) -> List[str]:
        """Files this source refers to (imports / paths), plus itself."""
        out = [rel]
        for other in files:
            if other == rel:
                continue
            stem = os.path.splitext(other)[0]
            dotted = stem.replace("/", ".")
            if dotted.endswith(".__init__"):
                dotted = dotted[: -len(".__init__")]
            parent, _, base = dotted.rpartition(".")
            if (dotted and re.search(rf"\b{re.escape(dotted)}\b", source)) or stem in source or \
                    (parent and base and re.search(rf"from\s+{re.escape(parent)}\s+import\s+[^\n]*\b{re.escape(base)}\b", source)):
                out.append(other)
        return out

    def _read_text(self, path: str) -> str:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    def _template(self, name: str) -> str:
        from ai.services.directory_manager import DirectoryManager
        dm = DirectoryManager()
        candidates = [os.path.join(dm.get_user_directory(), "task", name + ".md")]
        repo = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "assets", "templates", "user", "task", name + ".md")
        candidates.append(os.path.abspath(repo))
        for c in candidates:
            if os.path.isfile(c):
                return self._read_text(c)
        raise FileNotFoundError(f"Task template '{name}' not found.")

    def _system_prompt(self) -> str:
        from ai.services.directory_manager import DirectoryManager
        candidates = [os.path.join(DirectoryManager().get_system_dir(), "system-prompt", "task.md"),
                      os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..",
                                                   "assets", "templates", "system", "system-prompt", "task.md"))]
        for c in candidates:
            if os.path.isfile(c):
                return self._read_text(c)
        return "You are a headless code documentation engine. Output only the requested document."

    def build_messages(self, kind: str, rel: str, files: List[str]) -> Tuple[List[Dict[str, str]], str]:
        from ai.chat.chat import ChatRoles
        from ai.core.llms.base_llm import BaseModel

        source_path = os.path.join(self.config.source_root, rel)
        source = self._read_text(source_path)
        system = self._system_prompt()
        task = self._template(TASKS[kind][0])

        content = source
        if kind == "knowledge":
            doc = self.config.target_path("docs", rel)
            if os.path.isfile(doc):
                content = self._read_text(doc) + DOC_SEPARATOR + source

        shown_name = f"{os.path.basename(self.config.source_root)}/{rel}"
        manifest = self.manifest(kind, self.related_files(rel, source, files))
        context = (f"CURRENT SOURCE: {rel} | CURRENT TARGET: {self.config.target_rel(kind, rel)}\n"
                   f"MANIFEST (only the entries this file refers to):\n" + "\n".join(manifest))
        messages = [
            BaseModel.create_message(ChatRoles.SYSTEM, system),
            BaseModel.create_message(ChatRoles.USER, task),
            BaseModel.create_message(ChatRoles.USER, f"Filename: {shown_name} \nContent:\n```{content}```"),
            BaseModel.create_message(ChatRoles.USER, context),
        ]
        return messages, system

    # ------------------------------------------------------------------ run
    def build_file(self, kind: str, rel: str, files: Optional[List[str]] = None) -> Optional[str]:
        """Generates one output. Returns None on success, else the error (also recorded in the state)."""
        if self.llm_call is None:
            raise RuntimeError("No LLM available to build knowledge.")
        files = files if files is not None else self.scan()
        source_path = os.path.join(self.config.source_root, rel)
        messages, system = self.build_messages(kind, rel, files)

        limit = _context_limit(self.llm)
        est = int(sum(len(m.get("content", "")) for m in messages) / CHARS_PER_TOKEN)
        error: Optional[str] = None
        text = ""
        if limit and est > limit:
            error = f"too large for the model context (~{est} tokens > {limit})"
        else:
            for attempt in range(self.max_retries + 1):
                try:
                    text = clean_output(kind, self.llm_call(messages, system))
                except Exception as e:
                    error = f"LLM call failed: {e}"
                    break
                error = validate_output(kind, text)
                if error is None:
                    break
                from ai.chat.chat import ChatRoles
                from ai.core.llms.base_llm import BaseModel
                messages = messages + [BaseModel.create_message(
                    ChatRoles.USER, f"Your previous output was rejected ({error}). Output only the corrected document, nothing else.")]

        state = self._state(kind)
        entry = {"sha": _sha(source_path), "at": time.time()}
        if error is None:
            target = self.config.target_path(kind, rel)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w", encoding="utf-8") as f:
                f.write(text)
            entry["status"] = "ok"
        else:
            entry.update(status="error", error=error)
        state["files"][rel] = entry
        self._save_state(kind)
        return error

    def run(self, mode: str = "changed", files: Optional[Iterable[str]] = None, max_files: Optional[int] = None,
            diff_target: str = "master", force: bool = False) -> Dict[str, Any]:
        """
        Processes the planned files (docs before knowledge for each file).

        Args:
            mode: missing | changed | all | diff[:branch] (ignored when files are given).
            files: Explicit files to (re)generate.
            max_files: Stop after this many source files (the rest is reported as remaining).
            force: Regenerate every kind of a planned file, even when it is up to date.

        Returns:
            {"done": [...], "failed": [{"file", "kind", "error"}], "remaining": n, "seconds": s, "output": dir}
        """
        started = time.time()
        explicit = bool(files)
        queue = self.plan("files" if explicit else mode, files, diff_target)
        all_files = self.scan()
        limit = len(queue) if not max_files or max_files <= 0 else min(max_files, len(queue))
        done, failed = [], []
        processed = 0
        for index, rel in enumerate(queue[:limit], start=1):
            if self.cancel_event.is_set():
                break
            if force or explicit or mode == "all" or mode.startswith("diff"):
                kinds = list(self.config.kinds)
            else:
                wanted = ("missing", "error") if mode == "missing" else ("missing", "error", "outdated")
                kinds = [k for k in self.config.kinds if self.file_status(k, rel) in wanted]
            for kind in kinds:
                if self.cancel_event.is_set():
                    break
                t0 = time.time()
                self.on_progress({"event": "start", "file": rel, "kind": kind, "index": index, "total": limit})
                error = self.build_file(kind, rel, all_files)
                event = {"event": "done" if error is None else "failed", "file": rel, "kind": kind,
                         "index": index, "total": limit, "seconds": round(time.time() - t0, 1)}
                if error:
                    event["error"] = error
                    failed.append({"file": rel, "kind": kind, "error": error})
                self.on_progress(event)
            if not any(f["file"] == rel for f in failed):
                done.append(rel)
            processed += 1
        return {"done": done, "failed": failed, "remaining": max(0, len(queue) - processed),
                "seconds": round(time.time() - started, 1), "output": self.config.output_dir,
                "cancelled": self.cancel_event.is_set()}


# --------------------------------------------------------------------------- service

class KnowledgeService:
    """
    Glue used by the CLI, the agent tools, the server and the orchestrator: resolves the build
    config of a project, runs the builder, registers the outputs and reloads them in the store.
    """

    def __init__(self, store: Any = None, registry: Optional[KnowledgeRegistry] = None, config: Any = None):
        self.store = store
        self.registry = registry or KnowledgeRegistry()
        self.config = config
        self._lock = threading.Lock()   # one build at a time per process

    def build_config(self, project: str, **overrides) -> BuildConfig:
        return resolve_build_config(project, self.registry, self.config, **overrides)

    def status(self, project: str, **overrides) -> Dict[str, Any]:
        return KnowledgeBuilder(self.build_config(project, **overrides)).status()

    def build(self, project: str, llm: Any = None, llm_call: Optional[LLMCall] = None, mode: str = "changed",
              files: Optional[Iterable[str]] = None, max_files: Optional[int] = None,
              on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
              cancel_event: Optional[threading.Event] = None, force: bool = False,
              diff_target: str = "master", **overrides) -> Dict[str, Any]:
        cfg = self.build_config(project, **overrides)
        if not self._lock.acquire(blocking=False):
            raise RuntimeError("A knowledge build is already running.")
        try:
            builder = KnowledgeBuilder(cfg, llm=llm, llm_call=llm_call, on_progress=on_progress, cancel_event=cancel_event)
            report = builder.run(mode=mode, files=files, max_files=max_files, force=force, diff_target=diff_target)
        finally:
            self._lock.release()
        self.registry.set_build_config(
            cfg.project, source_root=os.path.relpath(cfg.source_root, cfg.project).replace(os.sep, "/"),
            extensions=cfg.extensions, output=cfg.output_dir)
        self.register_outputs(cfg)
        if self.store is not None:
            for rel in report["done"]:
                self.store.clear_stale(os.path.join(cfg.source_root, rel))
        return report

    def register_outputs(self, cfg: BuildConfig) -> None:
        """Registers the generated folders as the project's sources and (re)loads them in the store."""
        specs = [s for s in cfg.source_specs() if os.path.isdir(s.path)]
        self.registry.add_sources(cfg.project, specs)
        if self.store is None:
            return
        for spec in specs:
            try:
                self.store.add_source(spec, reload=True)
            except Exception as e:
                func.error(f"Knowledge: could not load {spec.path}: {e}")
