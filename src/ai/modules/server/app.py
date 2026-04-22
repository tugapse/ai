import os
import json
from color import Color
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from typing import List, Optional, Any
from .brain_hub import BrainHub
from .schemas import UpdateSessionRequest, ChatCompletionRequest

import functions as func

from fastapi.staticfiles import StaticFiles

class MIMETypeFixerMiddleware:
    def __init__(self, app):
        self.app = app
        func.debug("MIMETypeFixerMiddleware initialized.")

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http' and scope['path'].endswith(('.js', '.css', '.png', '.jpg', '.svg')):
            original_path = scope['path']
            mime_type = self._determine_mime_type(original_path)
            # Check if Content-Type header already exists to avoid duplicates
            if not any(header[0] == b'content-type' for header in scope['headers']):
                scope['headers'].append((b'Content-Type', mime_type.encode('utf-8')))
                func.debug(f"MIMETypeFixerMiddleware: Set Content-Type for {original_path} to {mime_type}")
            else:
                func.debug(f"MIMETypeFixerMiddleware: Content-Type already set for {original_path}, skipping.")
            await self.app(scope, receive, send)
        else:
            await self.app(scope, receive, send)

    def _determine_mime_type(self, path):
        if path.endswith('.js'):
            return 'application/javascript'
        elif path.endswith('.css'):
            return 'text/css'
        elif path.endswith('.png'):
            return 'image/png'
        elif path.endswith('.jpg') or path.endswith('.jpeg'):
            return 'image/jpeg'
        elif path.endswith('.svg'):
            return 'image/svg+xml'
        else:
            func.debug(f"MIMETypeFixerMiddleware: Could not determine specific MIME type for {path}, falling back to octet-stream.")
            return 'application/octet-stream' # Default fallback


def create_app(brain_hub: BrainHub, config: Any):
    func.log("Initializing FastAPI application...")

    SESSION_ROOT_DIR = Path(func.get_root_directory()) / "sessions" / "server"
    func.debug(f"Session root directory set to: {SESSION_ROOT_DIR}")

    app = FastAPI(title="JARVIS Neural Hub")
    app.add_middleware(MIMETypeFixerMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    func.log("CORS middleware added with all origins allowed.")

    @app.get("/api/health")
    async def health():
        model_name = getattr(brain_hub.get_stats(), 'model_chat_name', 'JARVIS')
        func.debug(f"Health check requested. Model: {model_name}")
        return {"status": "online", "model": model_name}

    @app.post("/api/v1/shutdown")
    async def shutdown():
        func.log("Neural Hub shutdown requested via API.", level="INFO")
        if brain_hub:
            func.debug("Unloading brain hub.")
            brain_hub.unload_brain()
        return {"status": "shutdown acknowledged"}


    @app.get("/api/v1/sessions")
    async def get_sessions(session_folder: Optional[str] = None):
        """
        Retrieves a list of all saved session IDs.
        Optionally filters by a specific sub-folder.
        """
        func.log(f"Retrieving sessions. Folder filter: {session_folder if session_folder else 'None'}")

        search_root_dir = SESSION_ROOT_DIR

        if session_folder:
            search_root_dir = SESSION_ROOT_DIR / session_folder
            func.debug(f"Searching sessions in specific folder: {search_root_dir}")

        if not search_root_dir.exists() or not search_root_dir.is_dir():
            func.log(f"Session search root directory not found or not a directory: {search_root_dir}", level="WARNING")
            return {"sessions": []}

        try:
            session_data_list = []
            func.debug(f"Scanning for session files in: {search_root_dir}")
            for file_path in search_root_dir.rglob("*.json"):
                if file_path.is_file():
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            session_content = json.load(f)

                        session_metadata = {
                            "session_id": session_content.get("session_id"),
                            "session_folder": session_content.get("session_folder"),
                            "session_title": session_content.get("session_title"),
                            "last_updated": session_content.get("last_updated"),
                            "filename": str(file_path.relative_to(search_root_dir).with_suffix(""))
                        }
                        session_data_list.append((file_path, session_metadata))
                        func.debug(f"Successfully loaded session metadata from: {file_path}")
                    except json.JSONDecodeError:
                        func.log(f"Skipping corrupted session file due to JSONDecodeError: {file_path}", level="ERROR")
                    except Exception as e:
                        func.log(f"Error processing session file {file_path}: {e}", level="ERROR")

            session_data_list.sort(
                key=lambda x: os.path.getmtime(str(x[0])),
                reverse=True
            )

            sessions_to_return = [data for _, data in session_data_list]
            func.log(f"Found {len(sessions_to_return)} sessions.")
            return {"sessions": sessions_to_return}

        except Exception as e:
            func.log(f"Failed to read sessions: {e}", level="ERROR")
            raise HTTPException(status_code=500, detail="Internal server error reading session files.")


    @app.get("/api/v1/sessions/{session_path:path}")
    async def get_session_content(session_path: str):
        func.log(f"Attempting to retrieve content for session: {session_path}")
        base_session_root_dir = SESSION_ROOT_DIR
        file_path = (base_session_root_dir / session_path).with_suffix(".json")
        func.debug(f"Constructed session file path: {file_path}")

        try:
            resolved_file_path = file_path.resolve()
            resolved_base_dir = base_session_root_dir.resolve()
            func.debug(f"Resolved paths - File: {resolved_file_path}, Base: {resolved_base_dir}")
            if not str(resolved_file_path).startswith(str(resolved_base_dir)):
                func.log(f"Access denied: Resolved path {resolved_file_path} is outside base directory {resolved_base_dir}", level="WARNING")
                raise HTTPException(status_code=403, detail="Access denied")
        except Exception as e:
            func.log(f"Invalid path resolution for {session_path}: {e}", level="ERROR")
            raise HTTPException(status_code=400, detail="Invalid path")

        if not resolved_file_path.exists() or not resolved_file_path.is_file():
            func.log(f"Session file not found at {resolved_file_path}", level="WARNING")
            raise HTTPException(status_code=404, detail="Session not found")

        try:
            with open(resolved_file_path, "r", encoding="utf-8") as f:
                content = json.load(f)
                content["filename"] = str(resolved_file_path.relative_to(base_session_root_dir).with_suffix(""))
                func.log(f"Successfully retrieved content for session: {session_path}")
                return content
        except json.JSONDecodeError:
            func.log(f"Session file corrupted for {session_path} at {resolved_file_path}", level="ERROR")
            raise HTTPException(status_code=500, detail="Session file corrupted")
        except Exception as e:
            func.log(f"Error reading session file {session_path}: {e}", level="ERROR")
            raise HTTPException(status_code=500, detail="Internal server error")


    @app.put("/api/v1/sessions/{session_path:path}")
    async def update_session_title(session_path: str, request: UpdateSessionRequest):
        """Updates the title of an existing session."""
        func.log(f"Attempting to update title for session: {session_path} to '{request.session_title}'")
        base_session_root_dir = SESSION_ROOT_DIR
        file_path = (base_session_root_dir / session_path).with_suffix(".json")
        func.debug(f"Constructed session file path for update: {file_path}")

        try:
            resolved_file_path = file_path.resolve()
            resolved_base_dir = base_session_root_dir.resolve()
            func.debug(f"Resolved paths for update - File: {resolved_file_path}, Base: {resolved_base_dir}")
            if not str(resolved_file_path).startswith(str(resolved_base_dir)):
                func.log(f"Access denied during title update: Resolved path {resolved_file_path} is outside base directory {resolved_base_dir}", level="WARNING")
                raise HTTPException(status_code=403, detail="Access denied")
        except Exception as e:
            func.log(f"Invalid path resolution for session title update {session_path}: {e}", level="ERROR")
            raise HTTPException(status_code=400, detail="Invalid path")

        if not resolved_file_path.exists() or not resolved_file_path.is_file():
            func.log(f"Session file not found for title update at {resolved_file_path}", level="WARNING")
            raise HTTPException(status_code=404, detail="Session not found")

        try:
            with open(resolved_file_path, "r", encoding="utf-8") as f:
                session_data = json.load(f)
            
            old_title = session_data.get("session_title", "N/A")
            session_data["session_title"] = request.session_title
            func.debug(f"Session '{session_path}' title changed from '{old_title}' to '{request.session_title}'")

            with open(resolved_file_path, "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=4)

            func.log(f"Successfully updated title for session '{session_path}' to '{request.session_title}'")
            return {"status": "success", "session_title": request.session_title}

        except json.JSONDecodeError:
            func.log(f"Session file corrupted during title update for {session_path} at {resolved_file_path}", level="ERROR")
            raise HTTPException(status_code=500, detail="Session file corrupted")
        except Exception as e:
            func.log(f"Failed to update session title for {session_path}: {e}", level="ERROR")
            raise HTTPException(status_code=500, detail="Internal server error")


    @app.delete("/api/v1/sessions/{session_path:path}")
    async def delete_session(session_path: str):
        """Deletes a specific session file."""
        func.log(f"Attempting to delete session: {session_path}")
        base_session_root_dir = SESSION_ROOT_DIR
        file_path = (base_session_root_dir / session_path).with_suffix(".json")
        func.debug(f"Constructed session file path for deletion: {file_path}")

        try:
            resolved_file_path = file_path.resolve()
            resolved_base_dir = base_session_root_dir.resolve()
            func.debug(f"Resolved paths for deletion - File: {resolved_file_path}, Base: {resolved_base_dir}")
            if not str(resolved_file_path).startswith(str(resolved_base_dir)):
                func.log(f"Access denied during deletion: Resolved path {resolved_file_path} is outside base directory {resolved_base_dir}", level="WARNING")
                raise HTTPException(status_code=403, detail="Access denied")
        except Exception as e:
            func.log(f"Invalid path resolution for session deletion {session_path}: {e}", level="ERROR")
            raise HTTPException(status_code=400, detail="Invalid path")

        if not resolved_file_path.exists() or not resolved_file_path.is_file():
            func.log(f"Session file not found for deletion at {resolved_file_path}", level="WARNING")
            raise HTTPException(status_code=404, detail="Session not found")

        try:
            resolved_file_path.unlink()
            func.log(f"Session deleted successfully: {session_path}", level="INFO")
            return {"status": "success", "message": f"Session {session_path} deleted."}

        except Exception as e:
            func.log(f"Failed to delete session file {session_path}: {e}", level="ERROR")
            raise HTTPException(status_code=500, detail="Internal server error")


    @app.post("/api/v1/chat/completions")
    @app.post("/api/v1/chat")
    async def chat_completions(request: ChatCompletionRequest):
        func.log(f"Chat completion request received. Stream: {request.stream}, Model: {request.model}")

        if not brain_hub:
            func.log("BrainHub not initialized for chat completion.", level="ERROR")
            raise HTTPException(status_code=503, detail="Orchestrator not initialized.")

        session_dir = SESSION_ROOT_DIR
        if request.session_folder:
            session_dir = os.path.join(session_dir, request.session_folder)
            func.debug(f"Using custom session folder: {request.session_folder}")

        os.makedirs(session_dir, exist_ok=True)
        func.debug(f"Ensured session directory exists: {session_dir}")

        target_session_id = request.session_id or config.get("ACTIVE_SESSION", "default")
        session_file = os.path.join(session_dir, f"{target_session_id}.json")

        func.debug(f"Routing memory to: {session_file}")

        brain_hub.route_memory(session_file,
                               session_title=request.session_title,
                               session_id=target_session_id,
                               session_folder=request.session_folder)
        func.debug(f"BrainHub memory routed to session: {target_session_id} in {request.session_folder or 'root'}")

        requested_model = (request.model or "default").strip().lower()
        system_prompt = request.system_prompt or ""
        func.debug(f"Getting brain for model: '{requested_model}' with system prompt: '{system_prompt[:50]}...'")
        brain_hub.get_brain(requested_model, system_prompt)

        formatted_messages = [{"role": m.role, "content": m.content} for m in request.messages]
        last_user_message = formatted_messages[-1]["content"] if formatted_messages else "N/A"
        func.debug(f"Adding user message to history: '{last_user_message[:100]}...'")
        brain_hub.add_history_message("user", last_user_message)

        if request.stream:
            func.log("Initiating streaming response for chat completion.")
            async def event_generator():
                try:
                    if brain_hub.orchestrator.llm is None:
                        func.log("LLM not initialized for streaming.", level="ERROR")
                        raise HTTPException(status_code=503, detail="LLM not initialized.")

                    raw_output = brain_hub.orchestrator.llm.chat(formatted_messages, stream=True)

                    func.debug("Streaming response generator started.")
                    completed_response = ""
                    for chunk in raw_output:
                        if chunk:
                            completed_response += str(chunk)
                            payload = {"choices": [{"delta": {"content": str(chunk)}}]}
                            yield f"data: {json.dumps(payload)}\n\n"
                            func.debug(f"Streamed chunk: '{str(chunk)[:50]}...'")

                    func.log("Streaming response completed.")
                    brain_hub.add_history_message("assistant", completed_response)
                    brain_hub.save_history_to_json(brain_hub.history_file)
                    func.debug("Assistant response saved to history.")
                    yield "data: [DONE]\n\n"

                except Exception as e:
                    func.log(f"Streaming Error: {e}", level="ERROR")
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"

            return StreamingResponse(event_generator(), media_type="text/event-stream")

        else:
            func.log("Initiating non-streaming response for chat completion.")
            try:
                if brain_hub.orchestrator.llm is None:
                    func.log("LLM not initialized for non-streaming.", level="ERROR")
                    raise HTTPException(status_code=503, detail="LLM not initialized.")

                raw_output = brain_hub.orchestrator.llm.chat(formatted_messages, stream=False)

                if isinstance(raw_output, str):
                    response_text = raw_output
                else:
                    response_text = "".join([str(chunk) for chunk in raw_output if chunk])
                
                func.debug(f"Non-streaming response received: '{response_text[:100]}...'")
                brain_hub.add_history_message("assistant", response_text)
                brain_hub.save_history_to_json(brain_hub.history_file)
                func.debug("Assistant response saved to history.")

                return {
                    "choices": [{
                        "message": {"role": "assistant", "content": response_text}
                    }]
                }
            except Exception as e:
                func.log(f"Inference Error during non-streaming chat completion: {e}", level="ERROR")
                raise HTTPException(status_code=500, detail=str(e))


    FRONTEND_BUILD_DIR = Path(__file__).resolve().parent / "frontend"
    func.log(f"Configuring static file serving from: {FRONTEND_BUILD_DIR}", level="INFO")

    if not FRONTEND_BUILD_DIR.is_dir():
        func.log(f"Frontend build directory not found at {FRONTEND_BUILD_DIR}. "
                 "Static files (Angular app) will not be served. "
                 "Please ensure your Angular app is built and 'FRONTEND_BUILD_DIR' is correctly configured.", level="WARNING")
    else:
        app.mount("/", StaticFiles(directory=FRONTEND_BUILD_DIR, html=True), name="static_app")
        func.debug(f"Static files mounted from {FRONTEND_BUILD_DIR} to root '/'.")

    func.log("FastAPI application setup complete.", level="INFO")
    return app