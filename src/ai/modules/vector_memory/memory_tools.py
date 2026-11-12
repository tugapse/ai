import ai.functions as func
from typing import Dict, Any, Optional, Callable
from ai.tools.base import tool

class MemoryTools:
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

    def get_tools(self) -> Dict[str, Callable]:
        """
        Maps tool names to their corresponding instance methods for the tool registry.

        Returns:
            Dict[str, Callable]: A dictionary mapping tool names to callable methods.
        """
        return { 
            "query_memory": self.query_memory, 
            "trigger_reflection": self.trigger_reflection 
        }

    def query_memory(self, **kwargs) -> Dict[str, Any]:
        """
        Recall facts from long-term memory: earlier findings, decisions, code details, or results that
        were removed from your context (look for 'Pruned' or 'Distilled' notes from SYSTEM).
        Try this before re-reading files you already explored.

        Args:
            query (string): A specific question, e.g. 'Which file configures the audio driver?'.
            top_k (int, optional): How many memory fragments to return. Default 3.

        Returns:
            results: the most relevant memory fragments, best first. FAILED if memory is disabled.
        """
        func.log("Tool execution: query_memory")
        
        if not self.vector_memory:
            return {"status": "FAILED", "error": "VectorMemory is currently disabled."}

        try:
            query = kwargs.get("query") or kwargs.get("search")
            if not query:
                return {"status": "FAILED", "error": "Parameter 'query' is required."}
                
            top_k = int(kwargs.get("top_k", 3))
            memories = self.vector_memory.retrieve_memories(query, top_k=top_k)

            if not memories:
                return {
                    "status": "SUCCESS",
                    "results": [],
                    "note": f"No matches found for '{query}'. Try a broader search term."
                }

            return {
                "status": "SUCCESS",
                "results": memories,
                "query": query,
                "count": len(memories)
            }

        except Exception as e:
            func.error(f"query_memory failed: {e}")
            return {"status": "FAILED", "error": str(e)}

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
            self.vector_memory.trigger_reflection()
            return {
                "status": "SUCCESS",
                "message": "Reflection cycle complete. Insights archived to LTM."
            }
        except Exception as e:
            func.error(f"trigger_reflection failed: {e}")
            return {"status": "FAILED", "error": str(e)}