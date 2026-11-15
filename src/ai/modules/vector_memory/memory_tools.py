import ai.functions as func
from typing import Dict, Any, Optional, Callable, List

from ai.tools.base import tool
from ai.tools.category import ToolCategory

# Kinds an agent may store explicitly with `remember`.
REMEMBER_KINDS = ("decision", "user_preference", "fact")


class MemoryTools(ToolCategory):
    """
    A service-oriented toolset for managing an agent's long-term memory.
    Connects the active agent to a persistent ChromaDB vector store.
    """

    def __init__(self, vector_memory_instance: Optional[Any] = None) -> None:
        """
        Initializes the MemoryTools with an active VectorMemory instance.

        Args:
            vector_memory_instance (Optional[Any]): The initialized VectorMemory object.
        """
        self.vector_memory = vector_memory_instance

    name = "memory"
    description = "Long-term memory: recall and store facts and decisions, also from earlier sessions."

    def get_category_tools(self) -> List[Callable]:
        return list(self.get_tools().values())

    def get_tools(self) -> Dict[str, Callable]:
        """
        Maps tool names to their corresponding instance methods for the tool registry.

        Returns:
            Dict[str, Callable]: A dictionary mapping tool names to callable methods.
        """
        return {
            "query_memory": self.query_memory,
            "remember": self.remember,
            "trigger_reflection": self.trigger_reflection,
        }

    @tool
    def query_memory(self, **kwargs) -> Dict[str, Any]:
        """
        Recall facts from long-term memory: decisions, user preferences, results of earlier tasks
        (also from previous sessions in this project), and details removed from your context
        (look for 'Pruned' or 'Distilled' notes from SYSTEM). Try this before re-reading files you already explored.

        Args:
            query (string): A specific question, e.g. 'Which file configures the audio driver?'.
            top_k (int, optional): How many memory fragments to return. Default 3.
            kind (string, optional): Only this kind: decision, user_preference, fact, episode, reflection, distilled_observation.

        Returns:
            results: the most relevant memory fragments, best first, each with its kind. FAILED if memory is disabled.
        """
        func.log("Tool execution: query_memory")

        if not self.vector_memory:
            return {"status": "FAILED", "error": "VectorMemory is currently disabled."}

        try:
            query = kwargs.get("query") or kwargs.get("search")
            if not query:
                return {"status": "FAILED", "error": "Parameter 'query' is required."}

            top_k = int(kwargs.get("top_k", 3) or 3)
            kind = kwargs.get("kind") or kwargs.get("type")
            memories = self.vector_memory.search(query, top_k=top_k, types=[kind] if kind else None)

            if not memories:
                return {
                    "status": "SUCCESS",
                    "results": [],
                    "note": f"No matches found for '{query}'. Try a broader search term."
                }

            return {
                "status": "SUCCESS",
                "results": [f"[{m['type']}] {m['content']}" for m in memories],
                "query": query,
                "count": len(memories)
            }

        except Exception as e:
            func.error(f"query_memory failed: {e}")
            return {"status": "FAILED", "error": str(e)}

    @tool
    def remember(self, **kwargs) -> Dict[str, Any]:
        """
        Save one durable fact to long-term memory so you (or another agent, in a later session) can recall it
        with query_memory. Use it for decisions and their reason, user preferences, and non-obvious facts about
        the project. Write a self-contained sentence; do not save things that are already in the code.

        Args:
            fact (string): The fact, e.g. 'User wants all config keys documented in README; decided on 2026-11-14.'.
            kind (string, optional): decision, user_preference or fact. Default fact.

        Returns:
            status SUCCESS with the memory id, FAILED if memory is disabled.
        """
        func.log("Tool execution: remember")
        if not self.vector_memory:
            return {"status": "FAILED", "error": "VectorMemory is currently disabled."}

        fact = kwargs.get("fact") or kwargs.get("content") or kwargs.get("text")
        if not fact or not str(fact).strip():
            return {"status": "FAILED", "error": "Parameter 'fact' is required."}
        kind = str(kwargs.get("kind") or "fact").strip().lower()
        if kind not in REMEMBER_KINDS:
            kind = "fact"
        try:
            memory_id = self.vector_memory.add_memory(str(fact), source="AGENT", memory_type=kind)
            return {"status": "SUCCESS", "id": (memory_id or "")[:12], "kind": kind}
        except Exception as e:
            func.error(f"remember failed: {e}")
            return {"status": "FAILED", "error": str(e)}

    @tool
    def trigger_reflection(self, **kwargs) -> Dict[str, Any]:
        """
        Save a summary of what you have learned recently into long-term memory, so query_memory can
        find it later. Call it after finishing a research phase or a refactor, or before handing off.

        Args:
            (none)

        Returns:
            status SUCCESS when the reflection was stored, FAILED if memory is disabled.
        """
        func.log("Tool execution: trigger_reflection")

        if not self.vector_memory:
            return {"status": "FAILED", "error": "VectorMemory is disabled."}

        try:
            count = self.vector_memory.trigger_reflection()
            return {
                "status": "SUCCESS",
                "message": f"Reflection cycle complete. {count or 0} insights archived to LTM."
            }
        except Exception as e:
            func.error(f"trigger_reflection failed: {e}")
            return {"status": "FAILED", "error": str(e)}
