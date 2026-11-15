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
        Initializes the ContextSentinel.

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
        self.last_pressure: float = 0.0  # Last measured context pressure (0..1+), for UIs
        self._warned_unmeasurable = False

    def current_limits(self) -> Tuple[int, int]:
        """
        (context window, output reserve) read from the connector on every check, so a model that
        reports its real window only after loading, or a model swap, is picked up. The reserve is
        capped at half the window: a large max_new_tokens must not leave no room to measure.
        """
        window, reserve = self.max_tokens, self.buffer
        try:
            window = int(self.connector.get_context_limit() or window)
        except Exception:
            pass
        try:
            reserve = int(self.connector.get_max_tokens() or reserve)
        except Exception:
            pass
        return window, max(0, min(reserve, window // 2))


    def enforce_limits(self, agent_name: str, memory_manager: Any, payload: Dict[str, Any], vector_memory: Optional[Any] = None,
                       overhead_chars: int = 0, keep_recent_results: int = 2) -> Tuple[Dict[str, Any], bool]:
        """
        Calculates context pressure based on payload size and performs in-place memory surgery if the threshold is exceeded.

        If pressure is high, it summarizes heavy tool outputs into technical facts, archives these facts to Vector Memory,
        and prunes the conversation history to maintain context efficiency.

        Args:
            agent_name (str): The name of the agent whose context is being monitored.
            memory_manager (Any): The manager responsible for retrieving and updating agent memory.
            payload (Dict[str, Any]): The current state payload containing context data.
            vector_memory (Optional[Any]): Optional vector memory store for archiving distilled facts.

        Returns:
            Tuple[Dict[str, Any], bool]: A tuple containing the potentially modified payload and a boolean indicating if compression/pruning occurred.
        """
        # Heuristic: ~3.2 characters per token. The system prompt and tool descriptions sent with
        # the payload (overhead_chars) count too.
        est_tokens = (len(json.dumps(payload, default=str)) + max(0, int(overhead_chars or 0))) / 3.2
        window, reserve = self.current_limits()
        delta = window - reserve
        if delta <= 0:
            if not self._warned_unmeasurable:
                func.log(f"Sentinel: cannot measure context pressure (window {window}, reserve {reserve}); disabled.", level="WARN")
                self._warned_unmeasurable = True
            self.last_pressure = 0.0
            return payload, False
        pressure = est_tokens / delta
        self.last_pressure = pressure


        if pressure < self.threshold:
            return payload, False

        func.out(f"{Color.YELLOW} Sentinel: Pressure {pressure:.1%}. Archiving facts to LTM...{Color.RESET}")

        agent_memory = memory_manager.get_agent_memory(agent_name)

        # The most recent tool results stay whole (the agent is working with them; summarizing them
        # makes it repeat the call). Only older heavy results are distilled.
        keep = max(0, int(keep_recent_results or 0))
        current = [i for i, m in enumerate(agent_memory.messages_received)
                   if m.get("from") == "SYSTEM" and "result" in m]
        protected = set(current[-keep:]) if keep else set()

        # Process active turn messages
        for i, msg in enumerate(agent_memory.messages_received):
            if msg.get("from") == "SYSTEM" and "result" in msg and i not in protected:
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
                        "status": msg["result"].get("status", "SUCCESS") if isinstance(msg["result"], dict) else "SUCCESS",
                        "summary": distilled,
                        "note": ("The full output was summarized to save context; this summary IS the result. "
                                 "Do not repeat the same call: work from the summary, and when you need exact "
                                 "lines use grep_file or read_file with start_line/end_line"
                                 + (", or query_memory." if vector_memory else "."))
                    }

        # Prune conversation history to the last 3 entries, plus the latest tool results still
        # needed to keep `keep_recent_results` of them (counting the ones of this turn)
        history = agent_memory.history
        still_needed = max(0, keep - len(protected))
        result_idx = [i for i, m in enumerate(history) if isinstance(m, dict) and "result" in m]
        keep_idx = set(result_idx[-still_needed:]) if still_needed else set()
        keep_idx.update(range(max(0, len(history) - 3), len(history)))
        agent_memory.history = [m for i, m in enumerate(history) if i in keep_idx]

        # Rebuild payload to reflect the new lean state
        payload["recent_outcomes"] = []
        payload["messages_received"] = agent_memory.messages_received
        payload["conversation_history"] = agent_memory.history

        return payload, True

    def _summarize_data(self, raw_result: Any) -> str:
        """
        Converts complex tool output into a dense, technical fact sheet using a sequential LLM call.

        This method prompts the LLM to act as a technical analyst, extracting key facts,
        preserving signatures, and explicitly deleting raw source code from the output.

        Args:
            raw_result (Any): The raw, verbose output from a tool execution.

        Returns:
            str: A plain text summary containing distilled technical facts.
        """
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