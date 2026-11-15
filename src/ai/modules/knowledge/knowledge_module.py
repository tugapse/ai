import threading
from typing import Any, Iterable, List, Optional

import ai.functions as func
from ai.modules.base_module import BaseModule
from ai.modules.knowledge.registry import KnowledgeRegistry, project_key
from ai.modules.knowledge.sources import SourceSpec, resolve_sources
from ai.modules.knowledge.store import KnowledgeStore


class KnowledgeModule(BaseModule):
    """
    Module wrapper for the KnowledgeStore.

    Sources come from config (KNOWLEDGE_SOURCES), the pipeline ("knowledge"), --knowledge, runtime
    feeds and the per-project registry: sources used once in a project folder are remembered and
    loaded again whenever an agent works there (ensure_project). Its tools are offered to agents
    only while at least one source is loaded (plus the build tools, always).
    """

    def __init__(self, db_path: Optional[str] = None, use_vectors: bool = False,
                 config_sources: Optional[Iterable[Any]] = None, registry: Optional[KnowledgeRegistry] = None,
                 config: Any = None, **kwargs):
        super().__init__(module_name="knowledge", **kwargs)
        self.db_path = db_path
        self.use_vectors = use_vectors
        self.config_sources = list(config_sources or [])
        self.registry = registry
        self.config = config
        self.service = None
        self._projects_loaded = set()
        self._lock = threading.Lock()

    def initialize(self, *args, **kwargs):
        from ai.modules.knowledge.builder import KnowledgeService
        with self._lock:
            if self._is_initialized:
                return
            self.registry = self.registry or KnowledgeRegistry()
            self._instance = KnowledgeStore(db_path=self.db_path, use_vectors=self.use_vectors)
            self.service = KnowledgeService(store=self._instance, registry=self.registry, config=self.config)
            self._instance.service = self.service
            self._is_initialized = True
        if self.config_sources:
            self.add_sources(self.config_sources, remember=False)

    def get_instance(self) -> KnowledgeStore:
        if not self._is_initialized:
            self.initialize()
        return self._instance

    def add_sources(self, entries: Iterable[Any], base_dir: Optional[str] = None,
                    project: Optional[str] = None, remember: bool = True) -> List[SourceSpec]:
        """
        Resolves and loads source entries (paths or {"id","path","kind"} dicts).
        Sources already loaded from the same path are skipped. Errors are logged, not raised.

        Args:
            remember: Register the loaded sources for ``project`` (default: base_dir) in the registry.

        Returns:
            The specs that are now loaded.
        """
        store = self.get_instance()
        loaded: List[SourceSpec] = []
        for spec in resolve_sources(list(entries or []), base_dir=base_dir):
            if store.has_source_path(spec.path):
                loaded.append(spec)
                continue
            try:
                store.add_source(spec)
                loaded.append(spec)
            except FileNotFoundError as e:
                func.error(f"Knowledge: {e}")
            except Exception as e:
                func.error(f"Knowledge: could not load '{spec.path}': {e}")
        owner = project or base_dir
        if remember and owner and loaded:
            try:
                self.registry.add_sources(owner, loaded)
            except Exception as e:
                func.error(f"Knowledge: could not remember sources: {e}")
        return loaded

    def ensure_project(self, project: str) -> List[SourceSpec]:
        """Loads the sources registered for a project folder (once per process)."""
        store = self.get_instance()
        key = project_key(project)
        specs = self.registry.sources(key)
        missing = [s for s in specs if not store.has_source_path(s.path)]
        loaded = []
        for spec in missing:
            try:
                store.add_source(spec)
                loaded.append(spec)
            except FileNotFoundError:
                func.log(f"Knowledge: registered source missing, skipped: {spec.path}", level="WARN")
            except Exception as e:
                func.error(f"Knowledge: could not load '{spec.path}': {e}")
        if loaded and key not in self._projects_loaded:
            func.log(f"Knowledge: loaded {len(loaded)} registered source(s) for {key}")
        self._projects_loaded.add(key)
        return loaded

    def shutdown(self):
        self._instance = None
        self.service = None
        self._is_initialized = False
