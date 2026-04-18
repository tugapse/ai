import os
import json
import zlib
import base64
from datetime import datetime
from typing import Dict, Any, Optional

import functions as func

class SessionVault:
    """
    Manages persistence for agent sessions.
    Stored in: [root]/agents/[session_id].json
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.storage_dir = os.path.join(func.get_root_directory(), "agents")
        self.session_path = os.path.join(self.storage_dir, f"{self.session_id}.json")
        self._ensure_storage()

    def _ensure_storage(self):
        """Ensures the agents folder exists."""
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
            func.log(f"SessionVault: Created agent storage at {self.storage_dir}")
        else:
            func.debug(f"SessionVault: Agent storage verified at {self.storage_dir}")

    def commit(self, orchestrator_state: Dict[str, Any], compress: bool = False):
        """
        Persists orchestrator state to the session's JSON journal.
        """
        func.debug(f"SessionVault: Committing state for {self.session_id} (Iter: {orchestrator_state.get('iteration')})")

        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "state": orchestrator_state,
            "version": "1.0"
        }

        try:
            data = json.dumps(payload)
            if compress:
                compressed_data = base64.b64encode(zlib.compress(data.encode())).decode()
                payload = {"compressed": True, "data": compressed_data, "timestamp": payload["timestamp"]}
                data = json.dumps(payload)

            # Use append mode to maintain a history (JSONL style despite .json extension)
            with open(self.session_path, "a", encoding="utf-8") as f:
                f.write(data + "\n")
            
            func.log(f"SessionVault: State committed to {self.session_path}")

        except Exception as e:
            func.error(f"SessionVault: Commit failed for {self.session_id}: {str(e)}")

    def hydrate(self, turn_index: int = -1) -> Optional[Dict[str, Any]]:
        """
        Re-inflates the orchestrator from the agent file.
        """
        if not os.path.exists(self.session_path):
            func.debug(f"SessionVault: No state file found at {self.session_path}. Starting fresh.")
            return None

        func.log(f"SessionVault: Hydrating from {self.session_path} (Index: {turn_index})")

        try:
            with open(self.session_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if not lines: return None
                
                entry = json.loads(lines[turn_index])

                if entry.get("compressed"):
                    decompressed = zlib.decompress(base64.b64decode(entry["data"]))
                    state = json.loads(decompressed)["state"]
                else:
                    state = entry["state"]
                
                func.log(f"SessionVault: Hydration successful. Resuming {state.get('current_agent')}")
                return state

        except Exception as e:
            func.error(f"SessionVault: Hydration failed: {str(e)}")
            return None

    def get_history_summary(self) -> list:
        """Returns turn-by-turn summary for debugging."""
        if not os.path.exists(self.session_path): return []
        
        history = []
        with open(self.session_path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                try:
                    entry = json.loads(line)
                    state = entry.get("state", {})
                    history.append({
                        "turn": i,
                        "timestamp": entry["timestamp"],
                        "agent": state.get("current_agent", "UNKNOWN"),
                        "iteration": state.get("iteration")
                    })
                except: continue
        return history