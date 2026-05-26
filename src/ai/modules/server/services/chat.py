from pathlib import Path
import os
import json
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

import ai.functions as func  
from ai.modules.server.brain_hub import BrainHub
from ai.modules.server.schemas import ChatCompletionRequest
from ai.services.prompt_loader import PromptLoader



class ChatSessionRouter:
    def __init__(self, session_root_dir: Path, config: Dict[str, Any]):
        self.session_root_dir = Path(session_root_dir).resolve()
        self.config = config or {}

    def build_session_path(self, request: ChatCompletionRequest):
        session_dir = self.session_root_dir
        if request.session_folder:
            session_dir = session_dir / request.session_folder

        os.makedirs(session_dir, exist_ok=True)
        target_session_id = request.session_id or self.config.get("ACTIVE_SESSION", "default")
        session_file = session_dir / f"{target_session_id}.json"
        return session_dir, session_file, target_session_id

    def route_memory(self, brain_hub: BrainHub, request: ChatCompletionRequest, session_file: Path, target_session_id: str):
        brain_hub.route_memory(
            str(session_file),
            session_title=getattr(request, "session_title", None),
            session_id=target_session_id,
            session_folder=getattr(request, "session_folder", None),
        )
        func.debug(
            f"BrainHub memory routed to session: {target_session_id} in {getattr(request, 'session_folder', 'root')}"
        )


class ChatMessageFormatter:
    @staticmethod
    def format_messages(messages: List[Any]):
        formatted_messages = [{"role": m.role, "content": m.content} for m in messages]
        last_user_message = formatted_messages[-1]["content"] if formatted_messages else "N/A"
        return formatted_messages, last_user_message


class ChatResponseHandler:
    def __init__(self, brain_hub: BrainHub):
        self.brain_hub = brain_hub

    def _ensure_llm_available(self, context: str):
        if self.brain_hub.orchestrator.llm is None:
            func.log(f"LLM not initialized for {context}.", level="ERROR")
            raise HTTPException(status_code=503, detail="LLM not initialized.")

    async def stream_response(self, formatted_messages: List[Dict[str, str]]) -> StreamingResponse:
        func.log("Initiating streaming response for chat completion.")
        self._ensure_llm_available("streaming")

        async def event_generator():
            try:
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

    def non_stream_response(self, formatted_messages: List[Dict[str, str]]):
        func.log("Initiating non-streaming response for chat completion.")
        self._ensure_llm_available("non-streaming")

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
            "choices": [{"message": {"role": "assistant", "content": response_text}}]
        }


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
        self.session_router = ChatSessionRouter(session_root_dir, config)
        self.message_formatter = ChatMessageFormatter()
        self.response_handler = ChatResponseHandler(brain_hub)

    def _resolve_system_prompt(self, system_prompt: Optional[str]) -> Optional[str]:
        if not system_prompt:
            return ""

        # Attempt file/template resolution for system prompt references.
        func.debug(f"Resolving system prompt reference: '{system_prompt}'")
        resolved_content = PromptLoader.load_system_prompt(self.brain_hub.config, system_prompt)
        if resolved_content and resolved_content.strip():
            func.debug(
                f"System prompt resolved successfully; content length={len(resolved_content)}"
            )
            return resolved_content

        func.debug(
            f"PromptLoader did not resolve '{system_prompt}' to a file; using literal prompt text."
        )
        return system_prompt

    def _resolve_brain(self, request: ChatCompletionRequest):
        # print(request)
        requested_model = (getattr(request, "model", "default") or "default").strip().lower()
        system_prompt = getattr(request, "system_prompt_content", '')
        resolved_system_prompt = self._resolve_system_prompt(system_prompt)
        print(resolved_system_prompt,end="\n\n")
        prompt_preview = (resolved_system_prompt or "<None>")[:50]
        print(
            f"Resolving brain: model='{requested_model}', system_prompt_preview='{prompt_preview}...'")
        self.brain_hub.get_brain(requested_model, resolved_system_prompt)



    async def chat_completion(self, request: ChatCompletionRequest):
        """ 
        Main entry point for handling chat completion requests.
        - Routes memory to session file
        - Resolves brain/model and system prompt
        - Delegates to response handler for streaming or non-streaming response
        """
        func.log(
            f"Chat completion request received. Stream: {getattr(request, 'stream', False)}, Model: {getattr(request, 'model', 'default')}"
        )

        if self.brain_hub is None:
            func.log("BrainHub not initialized for chat completion.", level="ERROR")
            raise HTTPException(status_code=503, detail="Orchestrator not initialized.")

        _, session_file, target_session_id = self.session_router.build_session_path(request)
        self.session_router.route_memory(self.brain_hub, request, session_file, target_session_id)

        self._resolve_brain(request)

        messages = getattr(request, "messages", [])
        formatted_messages, last_user_message = self.message_formatter.format_messages(messages)
        func.debug(f"Adding user message to history: '{last_user_message[:100]}...'")
        self.brain_hub.add_history_message("user", last_user_message)
        print(f"Formatted messages: {formatted_messages}")  # Debug print to verify message formatting
        if getattr(request, "stream", False):
            return await self.response_handler.stream_response(formatted_messages)

        try:
            return self.response_handler.non_stream_response(formatted_messages)
        except Exception as e:
            func.log(f"Inference Error during non-streaming chat completion: {e}", level="ERROR")
            raise HTTPException(status_code=500, detail=str(e))
