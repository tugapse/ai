import os
import time
import re
import hashlib
from typing import Any, List, Optional, Dict
from abc import ABC, abstractmethod
import functions as func
from chat.chat import ChatRoles
from core.llms.base_llm import BaseModel
from direct import ask
from .memory_tools import MemoryTools

try:
    from sentence_transformers import SentenceTransformer
    import chromadb
except ImportError:
    func.error("Missing dependencies: pip install sentence-transformers chromadb")
    SentenceTransformer = None
    chromadb = None

class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, text: str) -> List[float]:
        pass

class LanguageModelProvider(ABC):
    @abstractmethod
    def rate_importance(self, text: str) -> int:
        pass

    @abstractmethod
    def summarize_and_reflect(self, memories: List[str]) -> List[str]:
        pass

class VectorDBProvider(ABC):
    @abstractmethod
    def upsert(self, memory_id: str, vector: List[float], metadata: Dict[str, Any]):
        pass

    @abstractmethod
    def query(self, vector: List[float], top_k: int) -> List[Dict[str, Any]]:
        pass

class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        if SentenceTransformer is None:
            raise ImportError("sentence-transformers is not installed.")
        func.log(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)

    def embed(self, text: str) -> List[float]:
        return self.model.encode(text).tolist()

class LLMProvider(LanguageModelProvider):
    def __init__(self, llm : Optional[BaseModel]):
        self.llm = llm

    def rate_importance(self, text: str) -> int:
        prompt = {
            "instruction": "Rate the importance of this information for long-term retention (1-10). Respond with only an integer.",
            "task_context": text
        }
        response = self.send_raw_request(prompt, system_prompt="/no_think Response must be a single integer.")
        try:
            match = re.search(r'\d+', response)
            return int(match.group(0)) if match else 5
        except:
            return 5

    def summarize_and_reflect(self, memories: List[str]) -> List[str]:
        """Distills raw logs into permanent knowledge, facts, and user preferences."""
        memories_str = "\n".join(f"- {m}" for m in memories)
        prompt = {
            "instruction": (
                "Analyze these recent memories. Extract NEW facts about the user, "
                "project updates, or specific preferences. Ignore conversational filler. "
                "Output a bulleted list of concise insights."
            ),
            "task_context": memories_str
        }
        response = self.send_raw_request(prompt, system_prompt="You are a memory synthesis engine. Output only the list.")
        return [line.strip('- ').strip() for line in response.split('\n') if line.strip().startswith('-')]
    
    def send_raw_request(self, payload: Dict[str, Any], system_prompt: str = "") -> str:
        messages = [
            BaseModel.create_message(ChatRoles.SYSTEM, system_prompt),
            BaseModel.create_message(ChatRoles.USER, 
                f"CONTEXT:\n{payload.get('task_context')}\n\n"
                f"INSTRUCTION:\n{payload.get('instruction')}"
            )
        ]
        return self._execute_llm_call(messages).strip()
    
    def _execute_llm_call(self, messages: List[Dict[str, str]]) -> str:
        if not self.llm: return ""
        
        output_filename = f"{func.get_root_directory()}/logs/memory_output_active.md"
        try:
            ask(
                self.llm, 
                messages, 
                hide_think_anim=True, 
                print_output=False, 
                print_mode="line", 
                output_filename=output_filename, 
                write_to_file=True,
                stream=True
            )
            
            if os.path.exists(output_filename):
                with open(output_filename, "r", encoding="utf-8") as f:
                    content = f.read()
                return content
            return ""
                
        except Exception as e:
            func.error(f"LLM Execution failed: {e}")
            return ""

class ChromaDBProvider(VectorDBProvider):
    def __init__(self, path: str, session_id: str = "default"):
        if chromadb is None:
            raise ImportError("chromadb is not installed.")
        self.client = chromadb.PersistentClient(path=path)
        session_hash = hashlib.md5(session_id.encode()).hexdigest()
        collection_name = f"s_{session_hash}"
        func.log(f"Initializing ChromaDB: {collection_name}")
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def upsert(self, memory_id: str, vector: List[float], metadata: Dict[str, Any]):
        self.collection.upsert(ids=[memory_id], embeddings=[vector], metadatas=[metadata])

    def query(self, vector: List[float], top_k: int) -> List[Dict[str, Any]]:
        results = self.collection.query(query_embeddings=[vector], n_results=top_k)
        if not results or not results['ids'][0]: return []
        
        output = []
        for i in range(len(results['ids'][0])):
            similarity = 1.0 - results['distances'][0][i] if results['distances'] else 0.0
            output.append({'id': results['ids'][0][i], 'score': similarity, 'metadata': results['metadatas'][0][i]})
        return output

class VectorMemory:
    def __init__(
        self,
        session_id: str,
        llm: BaseModel | None = None,
        db_path: str = "./agent_ltm_db",
        recency_weight: float = 1.0,
        importance_weight: float = 1.0,
        relevance_weight: float = 1.0,
    ):
        self.db = ChromaDBProvider(path=db_path, session_id=session_id)
        self.embedder = SentenceTransformerEmbeddingProvider()
        self.llm = LLMProvider(llm=llm) if llm else None
        
        self.recency_weight = recency_weight
        self.importance_weight = importance_weight
        self.relevance_weight = relevance_weight
        self.tools = MemoryTools(self)

    def add_memory(self, content: str, source: str, memory_type: str = "observation"):
        if not content: return
        
        importance = self.llm.rate_importance(content) if self.llm else 5
        vector = self.embedder.embed(content)
        memory_id = hashlib.sha256(content.encode()).hexdigest()
        
        metadata = {
            "content": content,
            "source": source,
            "type": memory_type,
            "created_at": time.time(),
            "last_accessed_at": time.time(),
            "importance": importance,
        }
        
        self.db.upsert(memory_id=memory_id, vector=vector, metadata=metadata)
        func.log(f"Memory Archived: {content[:40]}... (ID: {memory_id[:8]})")

    def retrieve_memories(self, query: str, top_k: int = 5) -> List[str]:
        if not query: return []
        
        query_vector = self.embedder.embed(query)
        results = self.db.query(vector=query_vector, top_k=top_k * 3)
        
        ranked_results = []
        for res in results:
            recency = self._calculate_recency_score(res['metadata']['last_accessed_at'])
            importance = res['metadata']['importance'] / 10.0
            relevance = res['score']

            final_score = (
                self.recency_weight * recency +
                self.importance_weight * importance +
                self.relevance_weight * relevance
            )
            ranked_results.append((final_score, res['metadata']['content']))
            
        ranked_results.sort(key=lambda x: x[0], reverse=True)
        return [content for score, content in ranked_results[:top_k]]

    def trigger_reflection(self, lookback_k: int = 30):
        """
        Gathers recent high-importance memories and reduces them to core insights.
        This prevents the context window from being flooded with raw chat turns.
        """
        if not self.llm: return

        # Pull a broad slice of recent activity to synthesize
        recent = self.retrieve_memories("current context and recent interactions", top_k=lookback_k)
        
        if len(recent) < 5: 
            return

        insights = self.llm.summarize_and_reflect(recent)
        for insight in insights:
            # We save these as 'reflection' to distinguish them from raw data
            self.add_memory(insight, source="SELF_REFLECTION", memory_type="reflection")
        
        func.log(f"Reflection Complete: Generated {len(insights)} high-level insights.")

    @staticmethod
    def _calculate_recency_score(last_accessed_at: float, decay_factor: float = 0.99) -> float:
        hours = (time.time() - last_accessed_at) / 3600
        return decay_factor ** hours