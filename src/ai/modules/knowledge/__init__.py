"""
Project knowledge for agents: component JSON (extract-knowledge contract) and Markdown docs,
loaded from configured or fed sources into a graph + hybrid (keyword/semantic) search index.
"""

from ai.modules.knowledge.graph import KnowledgeGraph
from ai.modules.knowledge.sources import SourceSpec, resolve_sources, agent_allowed_sources
from ai.modules.knowledge.store import KnowledgeStore

__all__ = ["KnowledgeGraph", "KnowledgeStore", "SourceSpec", "resolve_sources", "agent_allowed_sources"]
