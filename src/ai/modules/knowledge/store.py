"""
KnowledgeStore: the agent's structural knowledge of a code base.

It loads two kinds of sources (see sources.py):
- component JSON (``extract-knowledge`` contract, schema.py): summaries, symbols, dependency edges;
- Markdown docs (docs_loader.py): heading sections for semantic search, linked to components.

Everything lives in memory (graph + lexical index). When the vector engine is installed, a
ChromaDB collection per source adds semantic search; it is synced incrementally in a
background thread, and lexical search is used until it is ready (or when it is unavailable).
"""

import hashlib
import json
import math
import os
import re
import threading
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import ai.functions as func
from ai.modules.knowledge.docs_loader import DocChunk, parse_markdown
from ai.modules.knowledge.graph import KnowledgeGraph
from ai.modules.knowledge.schema import (
    ComponentDoc, GraphEdge, GraphNode, looks_like_component, parse_component, path_key, relative_key,
)
from ai.modules.knowledge.sources import SourceSpec

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}
STRUCTURAL = "defines"
RRF_K = 60
VECTOR_CANDIDATES = 40


# --------------------------------------------------------------------------- records

@dataclass
class Component:
    key: str
    source_id: str
    source_path: str
    doc_path: str
    name: str
    type: str
    summary: str
    nodes: List[GraphNode]
    edges: List[GraphEdge]
    env_vars: List[str]
    ext_deps: List[str]
    side_effects: bool
    content_hash: str


@dataclass
class DocRecord:
    key: str
    source_id: str
    rel_path: str
    title: str
    chunks: List[DocChunk]
    links: List[str]
    source_file_key: Optional[str]
    content_hash: str

    @property
    def headings(self) -> List[str]:
        seen, out = set(), []
        for c in self.chunks:
            if c.heading not in seen:
                seen.add(c.heading)
                out.append(c.heading)
        return out


@dataclass
class Item:
    """One searchable unit: a component summary or a doc chunk."""
    id: str
    source_id: str
    kind: str            # component | doc_section
    key: str             # component key or doc key
    text: str
    heading: str = ""
    content_hash: str = ""


@dataclass
class SourceState:
    spec: SourceSpec
    components: Dict[str, Component] = field(default_factory=dict)
    docs: Dict[str, DocRecord] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    loaded_at: float = 0.0
    vector_ready: bool = False

    def items(self) -> List[Item]:
        out: List[Item] = []
        for c in self.components.values():
            symbols = ", ".join(n.name for n in c.nodes if n.name)[:600]
            text = f"{c.name} ({c.type}) {c.source_path}\n{c.summary}\nDefines: {symbols}"
            out.append(Item(id=f"c::{c.key}", source_id=c.source_id, kind="component", key=c.key,
                            text=text, content_hash=c.content_hash))
        for d in self.docs.values():
            for i, ch in enumerate(d.chunks):
                text = f"{d.title} - {ch.heading}\n{ch.text}"
                out.append(Item(id=f"d::{d.key}::{i}", source_id=d.source_id, kind="doc_section", key=d.key,
                                text=text, heading=ch.heading, content_hash=_hash(text)))
        return out


def _hash(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", "ignore")).hexdigest()


# --------------------------------------------------------------------------- lexical search

_TOKEN_RE = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+")
_STOP = {
    "the", "and", "for", "with", "this", "that", "from", "into", "are", "its", "is", "of", "to", "in", "on",
    "a", "an", "or", "by", "as", "be", "it", "at", "how", "what", "where", "which", "does", "do", "who",
    "um", "uma", "de", "da", "do", "das", "dos", "que", "onde", "como", "para", "em", "no", "na", "os", "as",
}


def _stem(word: str) -> str:
    """Very light plural folding ('invoices' -> 'invoice', 'classes' -> 'class')."""
    if len(word) > 4 and word.endswith("es") and word[-3] in "sxz":
        return word[:-2]
    if len(word) > 3 and word.endswith("s") and not word.endswith(("ss", "us", "is")):
        return word[:-1]
    return word


def tokenize(text: str) -> List[str]:
    """Lower-case word tokens; camelCase and snake_case identifiers are split into words too."""
    tokens: List[str] = []
    for raw in re.findall(r"[A-Za-z0-9_]+", text or ""):
        low = raw.lower()
        parts = [p.lower() for piece in raw.split("_") for p in _TOKEN_RE.findall(piece)]
        if len(parts) > 1 and len(low) > 2:
            tokens.append(low.replace("_", ""))
        for p in parts or [low]:
            if len(p) > 1 and p not in _STOP:
                tokens.append(_stem(p))
    return tokens


class LexicalIndex:
    """Small BM25 index over item texts."""

    def __init__(self, k1: float = 1.4, b: float = 0.75):
        self.k1, self.b = k1, b
        self.items: List[Item] = []
        self._tf: List[Counter] = []
        self._len: List[int] = []
        self._df: Counter = Counter()
        self._avg = 1.0

    def build(self, items: List[Item]) -> None:
        self.items = items
        self._tf = [Counter(tokenize(it.text)) for it in items]
        self._len = [sum(tf.values()) for tf in self._tf]
        self._df = Counter()
        for tf in self._tf:
            self._df.update(tf.keys())
        self._avg = (sum(self._len) / len(self._len)) if self._len else 1.0

    def search(self, query: str, allowed: Optional[Set[str]] = None, limit: int = 50) -> List[Tuple[int, float]]:
        terms = set(tokenize(query))
        if not terms or not self.items:
            return []
        n = len(self.items)
        scores: List[Tuple[int, float]] = []
        for i, tf in enumerate(self._tf):
            if allowed is not None and self.items[i].source_id not in allowed:
                continue
            s = 0.0
            for t in terms:
                f = tf.get(t)
                if not f:
                    continue
                idf = math.log(1 + (n - self._df[t] + 0.5) / (self._df[t] + 0.5))
                s += idf * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self._len[i] / self._avg))
            if s > 0:
                scores.append((i, s))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:limit]


# --------------------------------------------------------------------------- vector search

class VectorIndex:
    """One ChromaDB collection per source; synced incrementally by content hash."""

    def __init__(self, db_path: str, spec: SourceSpec):
        from ai.modules.vector_memory.vector_memory import ChromaDBProvider, get_embedder
        name = "kb_" + hashlib.md5(f"{spec.id}|{spec.path}".encode()).hexdigest()[:20]
        self.db = ChromaDBProvider(path=db_path, collection_name=name)
        self.embedder = get_embedder()

    def sync(self, items: List[Item]) -> Tuple[int, int]:
        existing = self.db.get()
        wanted = {it.id: it for it in items}
        stale = [i for i in existing if i not in wanted]
        todo = [it for it in items if existing.get(it.id, {}).get("hash") != it.content_hash]
        if stale:
            self.db.delete(ids=stale)
        for start in range(0, len(todo), 64):
            batch = todo[start:start + 64]
            vectors = self.embedder.embed_many([it.text for it in batch])
            self.db.upsert_many(
                ids=[it.id for it in batch],
                vectors=vectors,
                metadatas=[{"hash": it.content_hash, "kind": it.kind, "key": it.key} for it in batch],
            )
        return len(todo), len(stale)

    def query(self, vector: List[float], top_k: int) -> List[Tuple[str, float]]:
        return [(r["id"], r["score"]) for r in self.db.query(vector, top_k)]


# --------------------------------------------------------------------------- store

class KnowledgeStore:
    """
    In-memory knowledge base over one or more sources (component JSON and/or Markdown docs).
    Thread-safe; all public methods accept ``sources`` (a list of source ids) to restrict visibility.
    """

    def __init__(self, db_path: Optional[str] = None, use_vectors: bool = False, background: bool = True):
        """
        Args:
            db_path: Directory for the ChromaDB collections (required when use_vectors is True).
            use_vectors: Build semantic (embedding) indexes in addition to the lexical one.
            background: Sync the vector indexes in a background thread (False: synchronously, for tests).
        """
        from ai.modules.knowledge.tools import KnowledgeTools

        self.db_path = db_path
        self.use_vectors = bool(use_vectors and db_path)
        self.background = background
        self._lock = threading.RLock()
        self._sources: Dict[str, SourceState] = {}
        self._vectors: Dict[str, VectorIndex] = {}
        self._stale: Set[str] = set()
        self._stale_lock = threading.Lock()
        self.graph = KnowledgeGraph()
        self._components: Dict[str, Component] = {}
        self._docs_by_key: Dict[str, List[DocRecord]] = defaultdict(list)
        self._docs_by_component: Dict[str, List[DocRecord]] = defaultdict(list)
        self._doc_component: Dict[Tuple[str, str], Optional[str]] = {}
        self._items: List[Item] = []
        self._item_by_id: Dict[str, Item] = {}
        self._lex = LexicalIndex()
        self.service = None  # KnowledgeService (set by KnowledgeModule): builds and registers knowledge
        self.tools = KnowledgeTools(self)

    # ------------------------------------------------------------------ sources

    def has_sources(self) -> bool:
        with self._lock:
            return bool(self._sources)

    def source_ids(self) -> List[str]:
        with self._lock:
            return list(self._sources)

    def list_sources(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [{
                "id": s.spec.id,
                "path": s.spec.path,
                "kind": s.spec.kind,
                "components": len(s.components),
                "docs": len(s.docs),
                "sections": sum(len(d.chunks) for d in s.docs.values()),
                "errors": len(s.errors),
                "semantic": s.vector_ready,
                "stale": len([k for k in self._stale if k in s.components]),
            } for s in self._sources.values()]

    def has_source_path(self, path: str) -> bool:
        path = os.path.normpath(os.path.abspath(path))
        with self._lock:
            return any(s.spec.path == path for s in self._sources.values())

    def add_source(self, spec: SourceSpec, reload: bool = False) -> Dict[str, Any]:
        """
        Loads (or reloads) a source directory or file.

        Returns:
            {"id", "components", "docs", "errors"} for the loaded source.

        Raises:
            FileNotFoundError: If the path does not exist.
        """
        if not os.path.exists(spec.path):
            raise FileNotFoundError(f"Knowledge source not found: {spec.path}")
        with self._lock:
            if spec.id in self._sources and not reload and self._sources[spec.id].spec.path == spec.path:
                return self._source_summary(self._sources[spec.id])

        state = SourceState(spec=spec)
        files = [spec.path] if os.path.isfile(spec.path) else self._walk(spec.path)
        root = os.path.dirname(spec.path) if os.path.isfile(spec.path) else spec.path
        for file_path in files:
            self._load_file(state, file_path, root)
        state.loaded_at = time.time()

        with self._lock:
            self._sources[spec.id] = state
            self._rebuild()
        self._schedule_vector_sync(spec.id)
        summary = self._source_summary(state)
        func.log(f"Knowledge: source '{spec.id}' loaded ({summary['components']} components, "
                 f"{summary['docs']} docs, {summary['errors']} skipped) from {spec.path}")
        return summary

    def ingest_documents(self, source_id: str, documents: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Feeds documents directly (server API / tools), merging them into ``source_id``.

        Each document is either a component JSON object (extract-knowledge contract) or a
        Markdown document ``{"path": "ai/x.md", "content": "..."}``.
        """
        with self._lock:
            state = self._sources.get(source_id)
            if state is None:
                state = SourceState(spec=SourceSpec(id=source_id, path=f"memory://{source_id}", kind="auto"))
            else:
                state = SourceState(spec=state.spec, components=dict(state.components), docs=dict(state.docs),
                                    errors=list(state.errors))
        for i, doc in enumerate(documents or []):
            if not isinstance(doc, dict):
                state.errors.append(f"document {i}: not an object")
                continue
            if looks_like_component(doc):
                self._add_component(state, doc, origin=f"document {i}")
            elif doc.get("content") is not None and doc.get("path"):
                self._add_doc(state, str(doc["content"]), path_key(doc["path"]), str(doc["path"]))
            else:
                state.errors.append(f"document {i}: neither component JSON nor {{path, content}}")
        state.loaded_at = time.time()
        with self._lock:
            self._sources[source_id] = state
            self._rebuild()
        self._schedule_vector_sync(source_id)
        return self._source_summary(state)

    def remove_source(self, source_id: str) -> bool:
        with self._lock:
            if source_id not in self._sources:
                return False
            del self._sources[source_id]
            self._vectors.pop(source_id, None)
            self._rebuild()
            return True

    @staticmethod
    def _source_summary(state: SourceState) -> Dict[str, Any]:
        return {"id": state.spec.id, "components": len(state.components), "docs": len(state.docs),
                "errors": len(state.errors)}

    @staticmethod
    def _walk(root: str) -> List[str]:
        out = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith("."))
            for name in sorted(filenames):
                if name.lower().endswith((".json", ".md", ".markdown")):
                    out.append(os.path.join(dirpath, name))
        return out

    def _load_file(self, state: SourceState, file_path: str, root: str) -> None:
        kind = state.spec.kind
        lower = file_path.lower()
        try:
            if lower.endswith(".json") and kind in ("auto", "knowledge"):
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if looks_like_component(data):
                    self._add_component(state, data, origin=file_path)
                elif kind == "knowledge":
                    state.errors.append(f"{file_path}: not a component document")
            elif lower.endswith((".md", ".markdown")) and kind in ("auto", "docs"):
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
                self._add_doc(state, text, relative_key(file_path, root), os.path.relpath(file_path, root))
        except Exception as e:
            state.errors.append(f"{file_path}: {e}")
            func.debug(f"Knowledge: skipped {file_path}: {e}")

    def _add_component(self, state: SourceState, data: Dict[str, Any], origin: str) -> None:
        try:
            doc: ComponentDoc = parse_component(data)
        except Exception as e:
            state.errors.append(f"{origin}: {str(e).splitlines()[0]}")
            return
        c = doc.component
        key = path_key(c.source_path)
        if not key:
            state.errors.append(f"{origin}: empty source_path")
            return
        state.components[key] = Component(
            key=key,
            source_id=state.spec.id,
            source_path=c.source_path.lstrip("/"),
            doc_path=c.doc_path.lstrip("/"),
            name=c.name or key.rsplit("/", 1)[-1],
            type=c.type or "module",
            summary=(doc.vector_memory.semantic_summary or "").strip(),
            nodes=list(doc.graph_nodes),
            edges=list(doc.graph_edges),
            env_vars=list(doc.metadata.environment_variables),
            ext_deps=list(doc.metadata.external_dependencies),
            side_effects=bool(doc.metadata.has_side_effects),
            content_hash=_hash(json.dumps(data, sort_keys=True, default=str)),
        )

    @staticmethod
    def _add_doc(state: SourceState, text: str, key: str, rel_path: str) -> None:
        if not key:
            return
        parsed = parse_markdown(text, doc_key=key)
        if not parsed.chunks:
            return
        state.docs[key] = DocRecord(
            key=key, source_id=state.spec.id, rel_path=rel_path.replace("\\", "/"), title=parsed.title,
            chunks=parsed.chunks, links=parsed.links, source_file_key=parsed.source_file_key,
            content_hash=_hash(text),
        )

    # ------------------------------------------------------------------ indexes

    def _rebuild(self) -> None:
        """Rebuilds graph, doc links and lexical index from all sources (caller holds the lock)."""
        graph = KnowledgeGraph()
        components: Dict[str, Component] = {}
        for state in self._sources.values():
            for key, comp in state.components.items():
                components.setdefault(key, comp)

        for key, comp in components.items():
            graph.add_node(key, kind="component", name=comp.name, type=comp.type, path=comp.source_path,
                           source=comp.source_id)
            for n in comp.nodes:
                name = n.name or n.id.split("#", 1)[-1]
                if not name:
                    continue
                sid = f"{key}#{name}"
                graph.add_node(sid, kind="symbol", name=name, label=n.label, signature=n.signature, component=key)
                graph.add_relation(key, STRUCTURAL, sid)
            for e in comp.edges:
                target = path_key(e.target)
                if target and target != key:
                    graph.add_relation(key, (e.relation or "depends_on").lower(), target)

        docs_by_key: Dict[str, List[DocRecord]] = defaultdict(list)
        docs_by_component: Dict[str, List[DocRecord]] = defaultdict(list)
        doc_component: Dict[Tuple[str, str], Optional[str]] = {}
        for state in self._sources.values():
            for dkey, doc in state.docs.items():
                comp_key = self._match_component(dkey, components) or (
                    self._match_component(doc.source_file_key, components) if doc.source_file_key else None)
                doc_component[(state.spec.id, dkey)] = comp_key
                docs_by_key[dkey].append(doc)
                if comp_key:
                    docs_by_component[comp_key].append(doc)
                else:
                    graph.add_node(dkey, kind="doc", name=doc.title, path=doc.rel_path, source=doc.source_id)

        def node_for(k: str) -> str:
            return self._match_component(k, components) or k

        for state in self._sources.values():
            for dkey, doc in state.docs.items():
                src = doc_component.get((state.spec.id, dkey)) or dkey
                for link in doc.links:
                    dst = node_for(link)
                    if dst != src:
                        graph.add_relation(src, "references", dst)

        items: List[Item] = []
        for state in self._sources.values():
            items.extend(state.items())

        self.graph = graph
        self._components = components
        self._docs_by_key = docs_by_key
        self._docs_by_component = docs_by_component
        self._doc_component = doc_component
        self._items = items
        self._item_by_id = {it.id + "@" + it.source_id: it for it in items}
        self._lex.build(items)

    @staticmethod
    def _match_component(key: Optional[str], components: Dict[str, Component]) -> Optional[str]:
        if not key:
            return None
        if key in components:
            return key
        best = None
        for ck in components:
            if key.endswith("/" + ck) or ck.endswith("/" + key):
                if best is None or len(ck) > len(best):
                    best = ck
        return best

    def _schedule_vector_sync(self, source_id: str) -> None:
        if not self.use_vectors:
            return
        if self.background:
            threading.Thread(target=self._vector_sync, args=(source_id,), name=f"kb-sync-{source_id}",
                             daemon=True).start()
        else:
            self._vector_sync(source_id)

    def _vector_sync(self, source_id: str) -> None:
        with self._lock:
            state = self._sources.get(source_id)
            if state is None:
                return
            state.vector_ready = False
            items = state.items()
            spec = state.spec
        try:
            index = self._vectors.get(source_id) or VectorIndex(self.db_path, spec)
            added, removed = index.sync(items)
            with self._lock:
                if self._sources.get(source_id) is state:
                    self._vectors[source_id] = index
                    state.vector_ready = True
            func.log(f"Knowledge: semantic index for '{source_id}' ready ({added} embedded, {removed} removed).")
        except ImportError as e:
            func.log(f"Knowledge: semantic search unavailable ({e}); using keyword search.", level="WARN")
            self.use_vectors = False
        except Exception as e:
            func.error(f"Knowledge: semantic index for '{source_id}' failed: {e}")

    # ------------------------------------------------------------------ lookups

    def _allowed(self, sources: Optional[Iterable[str]]) -> Optional[Set[str]]:
        return None if sources is None else set(sources)

    def _visible_components(self, allowed: Optional[Set[str]]) -> Dict[str, Component]:
        if allowed is None:
            return self._components
        return {k: c for k, c in self._components.items() if c.source_id in allowed}

    def _visible_docs(self, docs: List[DocRecord], allowed: Optional[Set[str]]) -> List[DocRecord]:
        return [d for d in docs if allowed is None or d.source_id in allowed]

    def resolve_key(self, path: str, sources: Optional[Iterable[str]] = None) -> Optional[str]:
        """
        Maps a user/agent path ('src/ai/agents/memory_manager.py', '@ROOT/...', 'memory_manager')
        to the key of a known component or doc.
        """
        q = path_key(path)
        if not q:
            return None
        allowed = self._allowed(sources)
        with self._lock:
            keys = set(self._visible_components(allowed))
            keys.update(k for k, docs in self._docs_by_key.items() if self._visible_docs(docs, allowed))
            if q in keys:
                return q
            suffix = [k for k in keys if q.endswith("/" + k)]
            if suffix:
                return max(suffix, key=len)
            tail = sorted((k for k in keys if k.endswith("/" + q)), key=len)
            return tail[0] if tail else None

    def _component_view(self, comp: Component) -> Dict[str, Any]:
        return {"path": comp.source_path, "name": comp.name, "type": comp.type, "source": comp.source_id,
                "stale": comp.key in self._stale}

    def _display(self, key: str) -> str:
        comp = self._components.get(key)
        if comp:
            return comp.source_path
        node = self.graph.get_node(key) or {}
        return node.get("path") or key

    def get_component(self, path: str, sources: Optional[Iterable[str]] = None) -> Optional[Dict[str, Any]]:
        """Full record of a component: symbols, dependencies both ways, metadata, linked doc."""
        key = self.resolve_key(path, sources)
        if not key:
            return None
        allowed = self._allowed(sources)
        with self._lock:
            comp = self._visible_components(allowed).get(key)
            docs = self._visible_docs(self._docs_by_component.get(key, []) or self._docs_by_key.get(key, []), allowed)
            if comp is None:
                if not docs:
                    return None
                d = docs[0]
                return {"path": d.rel_path, "kind": "doc", "title": d.title, "sections": d.headings,
                        "references": [self._display(k) for k in self.graph.get_neighbors(key, "references")],
                        "referenced_by": [self._display(k) for k in self.graph.get_incoming(key, "references")]}
            view = self._component_view(comp)
            view.update({
                "summary": comp.summary,
                "symbols": [{"name": n.name, "kind": n.label, "signature": n.signature} for n in comp.nodes if n.name],
                "uses": sorted({self._display(d) for r, d in self.graph.edges_out(key) if r != STRUCTURAL}),
                "used_by": sorted({self._display(s) for r, s in self.graph.edges_in(key) if r != STRUCTURAL}),
                "environment_variables": comp.env_vars,
                "external_dependencies": comp.ext_deps,
                "has_side_effects": comp.side_effects,
            })
            if docs:
                view["doc"] = {"path": docs[0].rel_path, "sections": docs[0].headings}
            if view["stale"]:
                view["note"] = "This file was modified in this session; the knowledge may be outdated."
            return view

    def find_symbol(self, name: str, sources: Optional[Iterable[str]] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Where a class/function/method/variable is defined (exact name first, then case-insensitive/partial)."""
        name = (name or "").strip()
        if not name:
            return []
        short = name.rsplit(".", 1)[-1]
        allowed = self._allowed(sources)
        with self._lock:
            visible = self._visible_components(allowed)
            exact, loose = [], []
            for nid, attrs in self.graph.nodes().items():
                if attrs.get("kind") != "symbol" or attrs.get("component") not in visible:
                    continue
                sym = attrs.get("name", "")
                entry = {"symbol": sym, "kind": attrs.get("label", ""), "signature": attrs.get("signature", ""),
                         "path": visible[attrs["component"]].source_path}
                if sym == name or sym == short or sym.endswith("." + short):
                    exact.append(entry)
                elif short.lower() in sym.lower():
                    loose.append(entry)
            return (exact + loose)[:limit]

    def neighbors(self, path: str, direction: str = "both", relation: Optional[str] = None,
                  sources: Optional[Iterable[str]] = None) -> Optional[Dict[str, Any]]:
        """Graph neighbours of a component/doc: what it uses (out) and what uses it (in)."""
        key = self.resolve_key(path, sources)
        if not key:
            return None
        rel = relation.lower() if relation else None
        keep = (lambda r: r == rel) if rel else (lambda r: r != STRUCTURAL)
        with self._lock:
            out: Dict[str, Any] = {"path": self._display(key)}
            if direction in ("out", "both"):
                out["uses"] = [{"relation": r, "path": self._display(d)} for r, d in self.graph.edges_out(key) if keep(r)]
            if direction in ("in", "both"):
                out["used_by"] = [{"relation": r, "path": self._display(s)} for r, s in self.graph.edges_in(key) if keep(r)]
            return out

    def read_doc(self, path: str, section: Optional[str] = None, sources: Optional[Iterable[str]] = None,
                 max_chars: int = 4000) -> Optional[Dict[str, Any]]:
        """Documentation of a component: index of sections, or the text of one section."""
        key = self.resolve_key(path, sources)
        if not key:
            return None
        allowed = self._allowed(sources)
        with self._lock:
            docs = self._visible_docs(self._docs_by_component.get(key, []) or self._docs_by_key.get(key, []), allowed)
            if not docs:
                return None
            doc = docs[0]
            if not section:
                first = doc.chunks[0].text if doc.chunks else ""
                return {"path": doc.rel_path, "title": doc.title, "sections": doc.headings,
                        "overview": first[:1200]}
            wanted = section.strip().lower()
            parts = [c for c in doc.chunks if wanted in c.heading.lower()]
            if not parts:
                return {"path": doc.rel_path, "title": doc.title, "sections": doc.headings,
                        "error": f"No section matching '{section}'."}
            text, heading = "", parts[0].heading
            for c in parts:
                if c.heading != heading:
                    break
                text += (" " if text else "") + c.text
            return {"path": doc.rel_path, "section": heading, "text": text[:max_chars],
                    "truncated": len(text) > max_chars}

    def mark_stale(self, path: str) -> bool:
        """Flags a component as possibly outdated (its file was changed by the agent)."""
        key = self.resolve_key(path)
        if not key:
            return False
        with self._stale_lock:
            self._stale.add(key)
        return True

    def clear_stale(self, path: str) -> bool:
        """Removes the outdated flag of a component (its knowledge was regenerated)."""
        key = self.resolve_key(path)
        if not key:
            return False
        with self._stale_lock:
            found = key in self._stale
            self._stale.discard(key)
        return found

    def stale_keys(self) -> List[str]:
        with self._stale_lock:
            return sorted(self._stale)

    def is_stale(self, key: str) -> bool:
        return key in self._stale

    # ------------------------------------------------------------------ search

    def _vector_hits(self, query: str, allowed: Optional[Set[str]]) -> List[Item]:
        with self._lock:
            ready = [(sid, idx) for sid, idx in self._vectors.items()
                     if self._sources.get(sid) and self._sources[sid].vector_ready and (allowed is None or sid in allowed)]
        if not ready:
            return []
        try:
            vector = ready[0][1].embedder.embed(query)
        except Exception as e:
            func.debug(f"Knowledge: query embedding failed: {e}")
            return []
        hits: List[Tuple[float, Item]] = []
        for sid, idx in ready:
            try:
                for item_id, score in idx.query(vector, VECTOR_CANDIDATES):
                    it = self._item_by_id.get(item_id + "@" + sid)
                    if it:
                        hits.append((score, it))
            except Exception as e:
                func.debug(f"Knowledge: vector query on '{sid}' failed: {e}")
        hits.sort(key=lambda x: x[0], reverse=True)
        return [it for _, it in hits]

    def _group_key(self, it: Item) -> str:
        if it.kind == "component":
            return it.key
        return self._doc_component.get((it.source_id, it.key)) or f"doc:{it.key}"

    @staticmethod
    def _snippet(text: str, query: str, size: int = 240) -> str:
        terms = [t for t in tokenize(query) if len(t) > 2]
        low = text.lower()
        pos = min([p for p in (low.find(t) for t in terms) if p >= 0], default=0)
        start = max(0, pos - size // 3)
        snippet = text[start:start + size].strip()
        return ("..." if start > 0 else "") + snippet + ("..." if start + size < len(text) else "")

    def search(self, query: str, top_k: int = 5, sources: Optional[Iterable[str]] = None) -> List[Dict[str, Any]]:
        """
        Hybrid search (keyword BM25 + embeddings when ready, fused by reciprocal rank) over
        component summaries and doc sections, grouped by component.

        Returns:
            Best-first list of {path, kind, name, type, summary, sections[{heading, snippet}], source, stale, score}.
        """
        if not query or not query.strip():
            return []
        allowed = self._allowed(sources)
        with self._lock:
            lex = [self._lex.items[i] for i, _ in self._lex.search(query, allowed)]
        vec = self._vector_hits(query, allowed)

        fused: Dict[str, float] = defaultdict(float)
        by_id: Dict[str, Item] = {}
        for ranking in (lex, vec):
            for rank, it in enumerate(ranking):
                uid = it.id + "@" + it.source_id
                fused[uid] += 1.0 / (RRF_K + rank + 1)
                by_id[uid] = it
        if not fused:
            return []

        groups: Dict[str, Dict[str, Any]] = {}
        with self._lock:
            for uid, score in sorted(fused.items(), key=lambda x: x[1], reverse=True):
                it = by_id[uid]
                gk = self._group_key(it)
                g = groups.get(gk)
                if g is None:
                    g = groups[gk] = {"score": score, "sections": [], "_extra": 0.0}
                    comp = self._components.get(gk)
                    if comp and (allowed is None or comp.source_id in allowed):
                        g.update({"path": comp.source_path, "kind": "component", "name": comp.name,
                                  "type": comp.type, "summary": comp.summary, "source": comp.source_id,
                                  "stale": comp.key in self._stale})
                    else:
                        docs = self._docs_by_key.get(it.key, [])
                        doc = next((d for d in docs if d.source_id == it.source_id), docs[0] if docs else None)
                        g.update({"path": doc.rel_path if doc else it.key, "kind": "doc",
                                  "name": doc.title if doc else it.key, "type": "doc",
                                  "summary": (doc.chunks[0].text[:300] if doc and doc.chunks else ""),
                                  "source": it.source_id, "stale": False})
                elif not g["_extra"]:
                    g["_extra"] = score * 0.3  # one corroborating hit counts; many weak ones do not
                if it.kind == "doc_section" and len(g["sections"]) < 2 and \
                        all(s["heading"] != it.heading for s in g["sections"]):
                    g["sections"].append({"heading": it.heading, "snippet": self._snippet(it.text.split("\n", 1)[-1], query)})

        ranked = sorted(groups.values(), key=lambda g: g["score"] + g["_extra"], reverse=True)[:max(1, top_k)]
        top = ranked[0]["score"] + ranked[0]["_extra"] if ranked else 1.0
        for g in ranked:
            g["score"] = round((g["score"] + g.pop("_extra")) / top, 3)
        return ranked

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {"sources": len(self._sources), "components": len(self._components),
                    "docs": sum(len(v) for v in self._docs_by_key.values()), "items": len(self._items),
                    "graph": repr(self.graph)}
