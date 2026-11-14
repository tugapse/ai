"""Agent tools over the KnowledgeStore (registered only when at least one source is loaded)."""

import threading
from typing import Any, Callable, Dict, List, Optional

import ai.functions as func
from ai.modules.knowledge.project_paths import display_path
from ai.tools.base import tool
from ai.tools.category import ToolCategory


def _ellipsis(text: str, size: int) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= size else text[:size - 3].rstrip() + "..."


class KnowledgeTools(ToolCategory):
    """
    Tool callables bound to a KnowledgeStore.

    The orchestrator calls ``set_scope`` before each agent step so an agent only sees the
    sources its pipeline allows (thread-local: concurrent server runs do not interfere).
    """

    name = "knowledge"
    description = "Project knowledge base: what each file does, where symbols are, dependencies and docs."

    def __init__(self, store: Any):
        self.store = store
        self._scope = threading.local()

    def get_category_tools(self) -> List[Callable]:
        """Build tools always; query tools once at least one source is loaded."""
        tools = dict(self.get_build_tools())
        has_sources = getattr(self.store, "has_sources", None)
        if has_sources is None or has_sources():
            tools.update(self.get_tools())
        return list(tools.values())

    # --- scope ---
    def set_scope(self, sources: Optional[List[str]]) -> None:
        self._scope.sources = sources

    @property
    def scope(self) -> Optional[List[str]]:
        return getattr(self._scope, "sources", None)

    def set_llm(self, llm: Any) -> None:
        """LLM used by update_knowledge in this thread (the agent's model)."""
        self._scope.llm = llm

    @property
    def llm(self) -> Any:
        return getattr(self._scope, "llm", None)

    def get_tools(self) -> Dict[str, Callable]:
        """Tools that read the knowledge base (offered when at least one source is loaded)."""
        return {
            "search_knowledge": self.search_knowledge,
            "get_component": self.get_component,
            "knowledge_neighbors": self.knowledge_neighbors,
            "find_symbol": self.find_symbol,
            "read_doc": self.read_doc,
        }

    def get_build_tools(self) -> Dict[str, Callable]:
        """Tools that create or load knowledge (offered whenever the module is active)."""
        return {
            "knowledge_status": self.knowledge_status,
            "update_knowledge": self.update_knowledge,
            "ingest_knowledge": self.ingest_knowledge,
        }

    # --- tools ---
    @tool
    def search_knowledge(self, **kwargs) -> Dict[str, Any]:
        """
        Search the project knowledge base (component summaries and documentation) by meaning.
        Use it FIRST to find which files are responsible for something, before smart_search or reading files.

        Args:
            query (string): What you are looking for, e.g. 'where are tool call loops detected'.
            top_k (int, optional): How many components to return. Default 5.

        Returns:
            results: best-first components with path, summary and the most relevant doc sections.
            Files marked stale were changed in this session.
        """
        query = kwargs.get("query") or kwargs.get("search") or kwargs.get("pattern")
        if not query:
            return {"status": "FAILED", "error": "Parameter 'query' is required."}
        try:
            top_k = max(1, min(15, int(kwargs.get("top_k", 5) or 5)))
        except (TypeError, ValueError):
            top_k = 5
        try:
            hits = self.store.search(str(query), top_k=top_k, sources=self.scope)
        except Exception as e:
            func.error(f"search_knowledge failed: {e}")
            return {"status": "FAILED", "error": str(e)}
        if not hits:
            return {"status": "SUCCESS", "results": [], "note": f"Nothing found for '{query}'. Try other words or smart_search."}
        results = []
        for h in hits:
            entry = {"path": display_path(h["path"]), "kind": h["kind"], "summary": _ellipsis(h.get("summary", ""), 400)}
            if h.get("sections"):
                entry["doc_sections"] = h["sections"]
            if h.get("stale"):
                entry["stale"] = True
            results.append(entry)
        return {"status": "SUCCESS", "results": results, "hint": "Use get_component or read_doc on a path for details."}

    @tool
    def get_component(self, **kwargs) -> Dict[str, Any]:
        """
        Get the knowledge card of one source file: what it does, its classes/functions with signatures,
        which files it uses and which files use it, env vars and external dependencies.
        Cheaper than read_file when you only need the structure.

        Args:
            path (string): File path, e.g. 'src/ai/agents/memory_manager.py' (partial paths work).

        Returns:
            The component card, or FAILED when the file is not in the knowledge base.
        """
        path = kwargs.get("path") or kwargs.get("file") or kwargs.get("component")
        if not path:
            return {"status": "FAILED", "error": "Parameter 'path' is required."}
        card = self.store.get_component(str(path), sources=self.scope)
        if not card:
            return {"status": "FAILED", "error": f"'{path}' is not in the knowledge base. Try search_knowledge."}
        card = dict(card)
        card["path"] = display_path(card["path"])
        for key in ("uses", "used_by", "references", "referenced_by"):
            if key in card:
                card[key] = [display_path(p) for p in card[key]]
        if "doc" in card:
            card["doc"] = {**card["doc"], "path": display_path(card["doc"]["path"])}
        return {"status": "SUCCESS", **card}

    @tool
    def knowledge_neighbors(self, **kwargs) -> Dict[str, Any]:
        """
        Navigate the dependency graph: which files a file uses (out) and which files use it (in).
        Check 'in' before changing a file's public API to find the callers that may break.

        Args:
            path (string): File path, e.g. 'src/ai/config.py'.
            direction (string, optional): out, in or both. Default both.

        Returns:
            uses / used_by lists with the relation of each edge.
        """
        path = kwargs.get("path") or kwargs.get("file")
        if not path:
            return {"status": "FAILED", "error": "Parameter 'path' is required."}
        direction = str(kwargs.get("direction") or "both").lower()
        if direction not in ("in", "out", "both"):
            direction = "both"
        res = self.store.neighbors(str(path), direction=direction, relation=kwargs.get("relation"), sources=self.scope)
        if not res:
            return {"status": "FAILED", "error": f"'{path}' is not in the knowledge base."}
        res = dict(res)
        res["path"] = display_path(res["path"])
        for key in ("uses", "used_by"):
            if key in res:
                res[key] = [{**n, "path": display_path(n["path"])} for n in res[key]]
        return {"status": "SUCCESS", **res}

    @tool
    def find_symbol(self, **kwargs) -> Dict[str, Any]:
        """
        Find where a class, function, method or variable is defined, with its signature.

        Args:
            name (string): Symbol name, e.g. 'MemoryManager' or 'check_stagnation'.

        Returns:
            matches: list of {symbol, kind, signature, path}.
        """
        name = kwargs.get("name") or kwargs.get("symbol") or kwargs.get("query")
        if not name:
            return {"status": "FAILED", "error": "Parameter 'name' is required."}
        matches = self.store.find_symbol(str(name), sources=self.scope)
        if not matches:
            return {"status": "SUCCESS", "matches": [], "note": f"No symbol '{name}' in the knowledge base. Try smart_search."}
        return {"status": "SUCCESS", "matches": [{**m, "path": display_path(m["path"])} for m in matches]}

    @tool
    def read_doc(self, **kwargs) -> Dict[str, Any]:
        """
        Read the documentation of a file. Without 'section' you get the list of sections and an overview;
        with 'section' you get that section's text (e.g. 'Implementation Details', 'Public API').

        Args:
            path (string): File path, e.g. 'src/ai/agents/memory_manager.py'.
            section (string, optional): Part of a section heading to read.

        Returns:
            The overview and sections, or the section text. FAILED when the file has no documentation.
        """
        path = kwargs.get("path") or kwargs.get("file")
        if not path:
            return {"status": "FAILED", "error": "Parameter 'path' is required."}
        res = self.store.read_doc(str(path), section=kwargs.get("section"), sources=self.scope)
        if not res:
            return {"status": "FAILED", "error": f"No documentation for '{path}'."}
        if res.get("error"):
            return {"status": "FAILED", **res}
        return {"status": "SUCCESS", **res}

    @tool
    def ingest_knowledge(self, **kwargs) -> Dict[str, Any]:
        """
        Load a folder of knowledge into the knowledge base: component JSON files (extract-knowledge format)
        and/or Markdown documentation. Afterwards search_knowledge and the other knowledge tools can use it.

        Args:
            path (string): Folder (or file) inside the project, e.g. '@ROOT/docs'.
            id (string, optional): Name for this source. Default: the folder name.
            kind (string, optional): auto, knowledge (JSON only) or docs (Markdown only). Default auto.

        Returns:
            Number of components and docs loaded.
        """
        from ai.modules.knowledge.sources import parse_source_entry
        from ai.tools.base import get_project_root

        path = kwargs.get("path")
        if not path:
            return {"status": "FAILED", "error": "Parameter 'path' is required."}
        spec = parse_source_entry({"path": path, "id": kwargs.get("id"), "kind": kwargs.get("kind")},
                                  base_dir=get_project_root())
        if spec is None:
            return {"status": "FAILED", "error": f"Invalid source '{path}'."}
        root = get_project_root()
        if not (spec.path == root or spec.path.startswith(root.rstrip("/\\") + "/") or spec.path.startswith(root.rstrip("/\\") + "\\")):
            return {"status": "FAILED", "error": "The path must be inside the project."}
        try:
            summary = self.store.add_source(spec, reload=True)
            service = getattr(self.store, "service", None)
            if service is not None:
                service.registry.add_sources(root, [spec])   # remembered for this project
        except FileNotFoundError as e:
            return {"status": "FAILED", "error": str(e)}
        except Exception as e:
            func.error(f"ingest_knowledge failed: {e}")
            return {"status": "FAILED", "error": str(e)}
        return {"status": "SUCCESS", **summary}

    # --- building ---
    @tool
    def knowledge_status(self, **kwargs) -> Dict[str, Any]:
        """
        Show how complete and current the project's knowledge base is: how many source files have
        documentation and component knowledge, which are missing, outdated (source changed since) or failed,
        and which files were changed in this session.

        Args:
            (none)

        Returns:
            Coverage per kind (docs, knowledge) with the missing/outdated/error files, and the loaded sources.
        """
        from ai.tools.base import get_project_root
        service = getattr(self.store, "service", None)
        if service is None:
            return {"status": "FAILED", "error": "Knowledge building is not available."}
        try:
            status = service.status(get_project_root())
        except Exception as e:
            return {"status": "FAILED", "error": str(e)}
        changed = self.store.stale_keys() if hasattr(self.store, "stale_keys") else []
        return {"status": "SUCCESS", **status, "changed_this_session": changed[:20],
                "sources": [{"id": s["id"], "components": s["components"], "docs": s["docs"]} for s in self.store.list_sources()],
                "hint": "Use update_knowledge to generate missing or outdated files (a few per call)."}

    @tool
    def update_knowledge(self, **kwargs) -> Dict[str, Any]:
        """
        Generate or refresh the project's knowledge base (documentation + component knowledge) with the model,
        a few source files per call. Use it to create the knowledge of a project that has none, or to update
        the files you changed. Each file takes one or two model calls, so keep batches small.

        Args:
            paths (list, optional): Source files to (re)generate, e.g. '@ROOT/src/app/main.py'. Repeat the tag per file.
            mode (string, optional): Without paths: missing, changed (default: missing or outdated) or all.
            max_files (int, optional): Files to process in this call. Default 3, maximum 10.

        Returns:
            done / failed files and how many are still remaining; call again to continue.
        """
        from ai.tools.base import get_project_root, ensure_list
        service = getattr(self.store, "service", None)
        if service is None:
            return {"status": "FAILED", "error": "Knowledge building is not available."}
        if self.llm is None:
            return {"status": "FAILED", "error": "No model available to build knowledge."}
        paths = kwargs.get("paths") or kwargs.get("path") or kwargs.get("files")
        paths = [p for p in ensure_list(paths) if p] if paths else None
        mode = str(kwargs.get("mode") or "changed").lower()
        if mode not in ("missing", "changed", "all"):
            mode = "changed"
        try:
            max_files = max(1, min(10, int(kwargs.get("max_files", 3) or 3)))
        except (TypeError, ValueError):
            max_files = 3
        try:
            report = service.build(get_project_root(), llm=self.llm, mode=mode, files=paths, max_files=max_files)
        except Exception as e:
            func.error(f"update_knowledge failed: {e}")
            return {"status": "FAILED", "error": str(e)}
        if paths and not report["done"] and not report["failed"]:
            return {"status": "FAILED", "error": "None of the paths is a source file of this project's knowledge "
                                                 "(check the extension and that it is under the source root)."}
        return {"status": "SUCCESS" if not report["failed"] else "PARTIAL", "done": report["done"],
                "failed": report["failed"], "remaining": report["remaining"], "seconds": report["seconds"]}
