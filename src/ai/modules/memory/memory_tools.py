import functions as func
from typing import Dict, Any, Optional, Callable
from ai.tools.agent_tools import tool

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
        """
        return { 
            "query_memory": self.query_memory, 
            "trigger_reflection": self.trigger_reflection 
        }

    def query_memory(self, **kwargs) -> Dict[str, Any]:
        """
        ACTION: RECALL specific findings, code signatures, or technical context from Long-Term Memory (LTM).
        USE CASE: Mandatory to use if the information you need was recently 'Pruned' or 'Distilled' by the Sentinel, or if you need historical context without re-scanning physical files.
        BENEFIT: Prevents context window overflow and saves compute tokens.
        
        INPUTS:
            query (str): A detailed semantic search string (e.g., 'What was the specific bug in the audio driver?').
            top_k (int, optional): Number of memory fragments to retrieve. Defaults to 3.
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
        ACTION: SYNTHESIZE recent observations into high-level architectural insights and 'Project DNA'.
        USE CASE: Call this IMMEDIATELY after completing a major research phase, a code refactor, or before handing off to another agent. 
        PURPOSE: Consolidates messy turn-by-turn logs into permanent, structured knowledge for future 'query_memory' calls.
        
        INPUTS: 
            None required. 
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