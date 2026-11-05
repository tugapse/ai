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
    """
    Manages the routing and identification of chat sessions.

    This class is responsible for determining the correct directory and file path
    for a given chat session based on the request parameters and global configuration.
    """
    def __init__(self, session_root_dir: Path, config: Dict[str, Any]):
        """
        Initializes the ChatSessionRouter.

        Args:
            session_root_dir: The root directory where all chat sessions are stored.
            config: Global configuration dictionary.
        """
        self.session_root_dir = Path(session_root_dir).resolve()
        self.config = config or {}

    def build_session_path(self, request: ChatCompletionRequest) -> tuple[Path, Path, str]:
        """
        Determines the full path and ID for the target session.

        Args:
            request: The ChatCompletionRequest containing session details.

        Returns:
            A tuple containing:
            - session_dir: The directory where the session file resides.
            - session_file: The full Path object to the session JSON file.
            - target_session_id: The determined ID of the session.
        """
        session_dir = self.session_root_dir
        if request.session_folder:
            session_dir = session_dir / request.session_folder

        os.makedirs(session_dir, exist_ok=True)
        target_session_id = request.session_id or self.config.get(
            "ACTIVE_SESSION", "default"
        )
        session_file = session_dir / f"{target_session_id}.json"
        return session_dir, session_file, target_session_id

    def route_memory(
        self,
        brain_hub: BrainHub,
        request: ChatCompletionRequest,
        session_file: Path,
        target_session_id: str,
    ):
        """
        Routes the memory context to the specified session file within the BrainHub.

        Args:
            brain_hub: The BrainHub instance responsible for memory management.
            request: The chat request containing session metadata.
            session_file: The path to the session file.
            target_session_id: The ID of the session being routed to.
        """
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
    """
    Utility class for formatting raw message objects into a standardized list
    suitable for LLM API calls.
    """
    @staticmethod
    def format_messages(messages: List[Any]) -> tuple[List[Dict[str, str]], str]:
        """
        Converts a list of message objects into a list of dictionaries and extracts the last user message content.

        Args:
            messages: A list of message objects (expected to have role and content attributes).

        Returns:
            A tuple containing:
            - formatted_messages: A list of dictionaries in the format [{"role": str, "content": str}].
            - last_user_message: The content string of the last message sent by the user.
        """
        formatted_messages = [{"role": m.role, "content": m.content} for m in messages]
        last_user_message = (
            formatted_messages[-1]["content"] if formatted_messages else "N/A"
        )
        return formatted_messages, last_user_message


class ChatResponseHandler:
    """
    Handles the execution and formatting of the LLM response, supporting both
    streaming and non-streaming modes.
    """
    def __init__(self, brain_hub: BrainHub):
        """
        Initializes the ChatResponseHandler.

        Args:
            brain_hub: The BrainHub instance used to interact with the LLM and manage history.
        """
        self.brain_hub = brain_hub

    def _ensure_llm_available(self, context: str):
        """
        Checks if the LLM component within the BrainHub orchestrator is initialized.

        Args:
            context: A string describing the context (e.g., "streaming", "non-streaming").

        Raises:
            HTTPException: If the LLM is not initialized, returning a 503 Service Unavailable.
        """
        if self.brain_hub.orchestrator.llm is None:
            func.log(f"LLM not initialized for {context}.", level="ERROR")
            raise HTTPException(status_code=503, detail="LLM not initialized.")

    async def stream_response(
        self, formatted_messages: List[Dict[str, str]]
    ) -> StreamingResponse:
        """
        Generates a streaming HTTP response by calling the LLM in streaming mode.

        The response yields Server-Sent Events (SSE) data chunks. After completion,
        it saves the full assistant response to the history.

        Args:
            formatted_messages: The list of messages to send to the LLM.

        Returns:
            A StreamingResponse object configured for text/event-stream.
        """
        func.log("Initiating streaming response for chat completion.")
        self._ensure_llm_available("streaming")

        async def event_generator():
            try:
                raw_output = self.brain_hub.orchestrator.llm.chat(
                    formatted_messages, stream=True
                )
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
        """
        Generates a standard, non-streaming HTTP response by calling the LLM synchronously.

        The full response is returned immediately, and the assistant's reply is saved to history.

        Args:
            formatted_messages: The list of messages to send to the LLM.

        Returns:
            A dictionary representing the final chat completion response structure.
        """
        func.log("Initiating non-streaming response for chat completion.")
        self._ensure_llm_available("non-streaming")

        raw_output = self.brain_hub.orchestrator.llm.chat(
            formatted_messages, stream=False
        )
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

    This service manages the entire lifecycle of a chat interaction:
    routing memory to the correct session, resolving the appropriate model and system prompt,
    feeding messages to the LLM, and handling the final streaming or synchronous response.
    """

    def __init__(
        self, brain_hub: BrainHub, session_root_dir: Path, config: Dict[str, Any]
    ):
        """
        Initializes the ChatService.

        Args:
            brain_hub: The BrainHub instance managing models and memory.
            session_root_dir: The root directory for session storage.
            config: Global configuration settings.
        """
        self.brain_hub = brain_hub
        self.session_router = ChatSessionRouter(session_root_dir, config)
        self.message_formatter = ChatMessageFormatter()
        self.response_handler = ChatResponseHandler(brain_hub)

    def _resolve_system_prompt(self, system_prompt: Optional[str]) -> Optional[str]:
        """
        Resolves the system prompt content, supporting both direct text and file/template references.

        If the prompt is empty, an empty string is returned. If it references a file or template,
        PromptLoader attempts to load it. If loading fails or the content is empty, the literal
        prompt text is used.

        Args:
            system_prompt: The raw system prompt string, which may contain references.

        Returns:
            The fully resolved system prompt content as a string, or None if the input was None.
        """
        if not system_prompt:
            return ""

        # Attempt file/template resolution for system prompt references.
        func.debug(f"Resolving system prompt reference: '{system_prompt}'")
        resolved_content = PromptLoader.load_system_prompt(
            self.brain_hub.config, system_prompt
        )
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
        """
        Resolves the brain/model for the chat session based on the request parameters.

        This method determines the model ID, resolves the system prompt, and instructs
        the BrainHub to load the necessary brain configuration before inference.

        Args:
            request: The ChatCompletionRequest containing model and prompt specifications.
        """

        # print(request)
        requested_model_file: str | Any = (
            (getattr(request, "model", "default") or "default").strip().lower()
        )
        system_prompt: Any | str = getattr(request, "system_prompt_content", "")
        resolved_system_prompt: str | None = self._resolve_system_prompt(system_prompt)
        model_config_data = getattr(request, "model_config_data", None)

        self.brain_hub.get_brain(
            model_id=requested_model_file, 
            system_prompt=resolved_system_prompt,
            model_config_data=model_config_data
        )

    async def chat_completion(self, request: ChatCompletionRequest):
        """
        Main entry point for handling chat completion requests.

        This orchestrates the entire chat flow: memory routing, brain resolution,
        message formatting, and finally, calling the appropriate response handler
        (streaming or non-streaming).

        Args:
            request: The ChatCompletionRequest containing all necessary input data.

        Returns:
            Either a StreamingResponse (if stream=True) or a dictionary (if stream=False).

        Raises:
            HTTPException: If the BrainHub or LLM is not initialized (503), or if
                            inference fails (500).
        """
        func.log(
            f"Chat completion request received. Stream: {getattr(request, 'stream', False)}, Model: {getattr(request, 'model', 'default')}"
        )

        if self.brain_hub is None:
            func.log("BrainHub not initialized for chat completion.", level="ERROR")
            raise HTTPException(status_code=503, detail="Orchestrator not initialized.")

        _, session_file, target_session_id = self.session_router.build_session_path(
            request
        )
        self.session_router.route_memory(
            self.brain_hub, request, session_file, target_session_id
        )

        self._resolve_brain(request)

        messages = getattr(request, "messages", [])
        formatted_messages, last_user_message = self.message_formatter.format_messages(
            messages
        )
        func.debug(f"Adding user message to history: '{last_user_message[:100]}...'")
        self.brain_hub.add_history_message("user", last_user_message)
        print(
            f"Formatted messages: {formatted_messages}"
        )  # Debug print to verify message formatting
        if getattr(request, "stream", False):
            return await self.response_handler.stream_response(formatted_messages)

        try:
            return self.response_handler.non_stream_response(formatted_messages)
        except Exception as e:
            func.log(
                f"Inference Error during non-streaming chat completion: {e}",
                level="ERROR",
            )
            raise HTTPException(status_code=500, detail=str(e))