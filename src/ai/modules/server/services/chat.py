from pathlib import Path
import os
import json
from typing import Dict, Any, List, Optional

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

# Import core interfaces from your existing codebase
from ..brain_hub import BrainHub
from ..schemas import ChatCompletionRequest 

import functions as func  # reuse your existing logging/debug utilities


class ChatService:
    """
    High-level chat orchestration service.
    - Routes memory to a session file
    - Chooses brain/model and system prompt
    - Feeds user messages to the LLM
    - Streams or returns non-streaming responses
    """

    def __init__(self, brain_hub: BrainHub, session_root_dir: Path, config: Dict[str, Any]):
        self.brain_hub = brain_hub
        self.session_root_dir = Path(session_root_dir).resolve()
        self.config = config or {}

    def _build_session_path(self, request: ChatCompletionRequest):
        """
        Compute the memory/session file path for the current request.
        Creates the directory if needed.
        """
        session_dir = self.session_root_dir
        if request.session_folder:
            session_dir = session_dir / request.session_folder

        # Ensure the directory exists for writing
        os.makedirs(session_dir, exist_ok=True)

        target_session_id = request.session_id or self.config.get("ACTIVE_SESSION", "default")
        session_file = session_dir / f"{target_session_id}.json"
        return session_dir, session_file, target_session_id

    async def chat_completion(self, request: ChatCompletionRequest):
        """
        Main entry point to handle chat completions.
        Returns either a StreamingResponse (for streaming) or a dict (non-streaming).
        """
        func.log(f"Chat completion request received. Stream: {getattr(request, 'stream', False)}, Model: {getattr(request, 'model', 'default')}")

        if self.brain_hub is None:
            func.log("BrainHub not initialized for chat completion.", level="ERROR")
            raise HTTPException(status_code=503, detail="Orchestrator not initialized.")

        # Resolve/prepare session path
        session_dir, session_file, target_session_id = self._build_session_path(request)

        # Route memory to the target session
        self.brain_hub.route_memory(str(session_file),
                                    session_title=getattr(request, "session_title", None),
                                    session_id=target_session_id,
                                    session_folder=getattr(request, "session_folder", None))
        func.debug(f"BrainHub memory routed to session: {target_session_id} in {getattr(request, 'session_folder', 'root')}")

        # Prepare brain/model
        requested_model = (getattr(request, "model", "default") or "default").strip().lower()
        system_prompt = getattr(request, "system_prompt", "") or ""
        func.debug(f"Getting brain for model: '{requested_model}' with system prompt: '{system_prompt[:50]}...'")
        self.brain_hub.get_brain(requested_model, system_prompt)

        # Build message history
        messages = getattr(request, "messages", [])
        formatted_messages = [{"role": m.role, "content": m.content} for m in messages]
        last_user_message = formatted_messages[-1]["content"] if formatted_messages else "N/A"
        func.debug(f"Adding user message to history: '{last_user_message[:100]}...'")
        self.brain_hub.add_history_message("user", last_user_message)

        # Streaming path
        if getattr(request, "stream", False):
            func.log("Initiating streaming response for chat completion.")

            async def event_generator():
                try:
                    if self.brain_hub.orchestrator.llm is None:
                        func.log("LLM not initialized for streaming.", level="ERROR")
                        raise HTTPException(status_code=503, detail="LLM not initialized.")

                    raw_output = self.brain_hub.orchestrator.llm.chat(formatted_messages, stream=True)

                    func.debug("Streaming response generator started.")
                    completed_response = ""
                    for chunk in raw_output:
                        if chunk:
                            completed_response += str(chunk)
                            payload = {"choices": [{"delta": {"content": str(chunk)}}]}
                            yield f"data: {json.dumps(payload)}\n\n"
                            func.debug(f"Streamed chunk: '{str(chunk)[:50]}...'")

                    func.log("Streaming response completed.")
                    self.brain_hub.add_history_message("assistant", completed_response)
                    self.brain_hub.save_history_to_json(self.brain_hub.history_file)
                    func.debug("Assistant response saved to history.")
                    yield "data: [DONE]\n\n"

                except Exception as e:
                    func.log(f"Streaming Error: {e}", level="ERROR")
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"

            return StreamingResponse(event_generator(), media_type="text/event-stream")

        # Non-streaming path
        else:
            func.log("Initiating non-streaming response for chat completion.")
            try:
                if self.brain_hub.orchestrator.llm is None:
                    func.log("LLM not initialized for non-streaming.", level="ERROR")
                    raise HTTPException(status_code=503, detail="LLM not initialized.")

                raw_output = self.brain_hub.orchestrator.llm.chat(formatted_messages, stream=False)

                if isinstance(raw_output, str):
                    response_text = raw_output
                else:
                    response_text = "".join([str(chunk) for chunk in raw_output if chunk])

                func.debug(f"Non-streaming response received: '{response_text[:100]}...'")
                self.brain_hub.add_history_message("assistant", response_text)
                self.brain_hub.save_history_to_json(self.brain_hub.history_file)
                func.debug("Assistant response saved to history.")

                return {
                    "choices": [{
                        "message": {"role": "assistant", "content": response_text}
                    }]
                }
            except Exception as e:
                func.log(f"Inference Error during non-streaming chat completion: {e}", level="ERROR")
                raise HTTPException(status_code=500, detail=str(e))