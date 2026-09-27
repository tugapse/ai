import json
from typing import Dict, Any, Optional, Tuple
import ai.functions as func
from ai.color import Color

class ContextSentinel:
    """
    Monitors context pressure and performs distilled compression of tool outputs.
    Archives technical facts to Long-Term Memory (LTM) before pruning state.
    """

    def __init__(self, connector: Any, threshold: float = 0.8, max_tokens: int = 20000, buffer: int = 1024):
        """
        Args:
            connector (Any): LLM connector for 'raw' distillation requests.
            threshold (float): Percentage of context used to trigger compression.
            max_tokens (int): Hardware context limit of the local GGUF engine.
            buffer (int): Safety buffer to prevent hitting hard limits.
        """
        self.connector = connector
        self.threshold = threshold
        self.max_tokens = max_tokens
        self.buffer = buffer  # Safety buffer to prevent hitting hard limits
        

    def enforce_limits(self, agent_name: str, memory_manager: Any, payload: Dict[str, Any], vector_memory: Optional[Any] = None) -> Tuple[Dict[str, Any], bool]:
        """
        Calculates pressure and performs in-place memory surgery if over threshold.
        """
        # Heuristic: 4 characters per token
        est_tokens = len(json.dumps(payload)) / 3.2
        delta = (self.max_tokens - self.buffer )
        pressure = est_tokens / delta if delta > 0 else 1

        if delta <= 0:
            func.log("DELTA  WAS ZERO ", level="WARN")
            return payload, False


        if pressure < self.threshold:
            return payload, False

        func.out(f"{Color.YELLOW}◈ Sentinel: Pressure {pressure:.1%}. Archiving facts to LTM...{Color.RESET}")

        agent_memory = memory_manager.get_agent_memory(agent_name)

        # Process active turn messages
        for i, msg in enumerate(agent_memory.messages_received):
            if msg.get("from") == "SYSTEM" and "result" in msg:
                # Trigger distillation for heavy outputs (code/logs)
                if len(json.dumps(msg["result"])) > 2000:
                    distilled = self._summarize_data(msg["result"])
                    
                    # LINK: Archive to Vector Memory before we prune the active context
                    if vector_memory:
                        vector_memory.add_memory(
                            content=distilled, 
                            source=f"SENTINEL_{agent_name}", 
                            memory_type="distilled_observation"
                        )

                    # Update source memory with high-level facts
                    agent_memory.messages_received[i]["result"] = {
                        "status": "SUCCESS",
                        "summary": distilled,
                        "metadata": "Raw code moved to LTM by Sentinel."
                    }

        # Prune conversation history to the last 3 turns
        agent_memory.history = agent_memory.history[-3:]

        # Rebuild payload to reflect the new lean state
        payload["recent_outcomes"] = []
        payload["messages_received"] = agent_memory.messages_received
        payload["conversation_history"] = agent_memory.history

        return payload, True

    def _summarize_data(self, raw_result: Any) -> str:
        """Sequential LLM call to convert implementation code into technical facts."""
        prompt = {
            "instruction": (
                "ACT AS A TECHNICAL ANALYST. Summarize the tool output into a dense fact sheet. "
                "1. Keep file paths and function signatures. 2. Describe logic intent. "
                "3. DELETE ALL RAW SOURCE CODE. Output plain text summary only."
            ),
            "task_context": json.dumps(raw_result)
        }
        # Blocking call to ensure sequential stability
        return self.connector.send_raw_request(prompt, system_prompt="Fact-Sheet Architect")