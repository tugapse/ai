import os
import json
from color import Color
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from typing import List, Optional, Any
from .brain_hub import BrainHub
from .schemas import UpdateSessionRequest , ChatCompletionRequest

import functions as func




def create_app(brain_hub: BrainHub, config: Any):
    app = FastAPI(title="JARVIS Neural Hub")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health():
        return {"status": "online", "model": getattr(brain_hub.get_stats(), 'model_chat_name', 'JARVIS')}

    @app.post("/v1/shutdown")
    async def shutdown():
        if brain_hub:
            brain_hub.unload_brain()
        func.log("Neural Hub shutdown requested via API.")
        return {"status": "shutdown acknowledged"}
    
   
   
   
    @app.get("/v1/sessions")
    async def get_sessions(session_folder: Optional[str] = None):
        """
        Retrieves a list of all saved session IDs.
        Optionally filters by a specific sub-folder.
        """
        # Base directory where all sessions are stored
        base_session_root_dir = Path(func.get_root_directory()) / "logs" / "server" / "sessions"
        
        # Determine the directory to start searching from
        search_root_dir = base_session_root_dir
        if session_folder:
            search_root_dir = base_session_root_dir / session_folder
            
        if not search_root_dir.exists() or not search_root_dir.is_dir():
            return {"sessions": []}
            
        try:
            session_data_list = []
            for file_path in search_root_dir.rglob("*.json"):
                if file_path.is_file():
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            session_content = json.load(f)
                        
                        # Extract desired metadata and exclude 'messages'
                        session_metadata = {
                            "session_id": session_content.get("session_id"),
                            "session_folder": session_content.get("session_folder"),
                            "session_title": session_content.get("session_title"),
                            "last_updated": session_content.get("last_updated"),
                            "filename": str(file_path.relative_to(search_root_dir).with_suffix(""))
                        }
                        session_data_list.append((file_path, session_metadata))
                    except json.JSONDecodeError:
                        func.log(f"Skipping corrupted session file: {file_path}", level="ERROR")
                    except Exception as e:
                        func.log(f"Error processing session file {file_path}: {e}", level="ERROR")
            
            # Sort by modification time, most recent first
            session_data_list.sort(
                key=lambda x: os.path.getmtime(str(x[0])), 
                reverse=True
            )
            
            # Extract only the metadata dictionaries for the final response
            sessions_to_return = [data for _, data in session_data_list]
            
            return {"sessions": sessions_to_return}
            
        except Exception as e:
            print(f"{Color.RED}Failed to read sessions: {e}{Color.RESET}")
            raise HTTPException(status_code=500, detail="Internal server error reading session files.")




    @app.get("/v1/sessions/{session_path:path}")
    async def get_session_content(session_path: str):
        base_session_root_dir = Path(func.get_root_directory()) / "logs" / "server" / "sessions"
        file_path = (base_session_root_dir / session_path).with_suffix(".json")
        
        # Prevent path traversal attacks (e.g., passing "../../etc/shadow")
        try:
            resolved_file_path = file_path.resolve()
            resolved_base_dir = base_session_root_dir.resolve()
            if not str(resolved_file_path).startswith(str(resolved_base_dir)):
                raise HTTPException(status_code=403, detail="Access denied")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid path")

        if not resolved_file_path.exists() or not resolved_file_path.is_file():
            raise HTTPException(status_code=404, detail="Session not found")
            
        try:
            with open(resolved_file_path, "r", encoding="utf-8") as f:
                content = json.load(f)
                content["filename"] = str(resolved_file_path.relative_to(base_session_root_dir).with_suffix(""))
                return content
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="Session file corrupted")

    
    
    @app.put("/v1/sessions/{session_path:path}")
    async def update_session_title(session_path: str, request: UpdateSessionRequest):
        """Updates the title of an existing session."""
        base_session_root_dir = Path(func.get_root_directory()) / "logs" / "server" / "sessions"
        file_path = (base_session_root_dir / session_path).with_suffix(".json")
        
        # Security check: Prevent path traversal
        try:
            resolved_file_path = file_path.resolve()
            resolved_base_dir = base_session_root_dir.resolve()
            if not str(resolved_file_path).startswith(str(resolved_base_dir)):
                raise HTTPException(status_code=403, detail="Access denied")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid path")

        if not resolved_file_path.exists() or not resolved_file_path.is_file():
            raise HTTPException(status_code=404, detail="Session not found")
            
        try:
            # Load the existing session data
            with open(resolved_file_path, "r", encoding="utf-8") as f:
                session_data = json.load(f)
                
            # Update the title
            session_data["session_title"] = request.session_title
            
            # Save it back to the file
            with open(resolved_file_path, "w", encoding="utf-8") as f:
                json.dump(session_data, f, indent=4)
                
            return {"status": "success", "session_title": request.session_title}
            
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="Session file corrupted")
        except Exception as e:
            func.log(f"Failed to update session title: {e}", level="ERROR")
            raise HTTPException(status_code=500, detail="Internal server error")
        

    @app.delete("/v1/sessions/{session_path:path}")
    async def delete_session(session_path: str):
        """Deletes a specific session file."""
        base_session_root_dir = Path(func.get_root_directory()) / "logs" / "server" / "sessions"
        file_path = (base_session_root_dir / session_path).with_suffix(".json")
        
        # Security check: Prevent path traversal
        try:
            resolved_file_path = file_path.resolve()
            resolved_base_dir = base_session_root_dir.resolve()
            if not str(resolved_file_path).startswith(str(resolved_base_dir)):
                raise HTTPException(status_code=403, detail="Access denied")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid path")

        if not resolved_file_path.exists() or not resolved_file_path.is_file():
            raise HTTPException(status_code=404, detail="Session not found")
            
        try:
            # Delete the file securely
            resolved_file_path.unlink()
            func.log(f"Session deleted: {session_path}")
            
            return {"status": "success", "message": f"Session {session_path} deleted."}
            
        except Exception as e:
            func.log(f"Failed to delete session file: {e}", level="ERROR")
            raise HTTPException(status_code=500, detail="Internal server error")


    @app.post("/v1/chat/completions")
    @app.post("/v1/chat")
    async def chat_completions(request: ChatCompletionRequest):
        if not brain_hub:
            raise HTTPException(status_code=503, detail="Orchestrator not initialized.")

        # Resolve session directory and ensure it exists
        session_dir = os.path.join(func.get_root_directory(), "logs", "server", "sessions")
        if request.session_folder:
            session_dir = os.path.join(session_dir, request.session_folder)
        
        os.makedirs(session_dir, exist_ok=True)

        # Fallback to the active session state if no ID is provided by the client
        # Note: Replace "ACTIVE_SESSION" with your specific ProgramSetting enum if applicable
        target_session_id = request.session_id or config.get("ACTIVE_SESSION", "default")
        session_file = os.path.join(session_dir, f"{target_session_id}.json")

        # Note: Replace "PRINT_DEBUG" with your specific ProgramSetting enum (e.g., ProgramSetting.PRINT_DEBUG)
        if config.get("PRINT_DEBUG"):
            print(f"{Color.YELLOW}[DEBUG] Routing memory to: {session_file}{Color.RESET}")

        brain_hub.route_memory(session_file, 
                               session_title=request.session_title, 
                               session_id=target_session_id, 
                               session_folder=request.session_folder)
        requested_model = (request.model or "default").strip().lower()
        system_prompt = request.system_prompt or ""
        brain_hub.get_brain(requested_model, system_prompt)

        formatted_messages = [{"role": m.role, "content": m.content} for m in request.messages]
        brain_hub.add_history_message("user", formatted_messages[-1]["content"])
        
        if request.stream:
            async def event_generator():
                try:
                    if brain_hub.orchestrator.llm is None:
                        raise HTTPException(status_code=503, detail="LLM not initialized.") 
                    
                    raw_output = brain_hub.orchestrator.llm.chat(formatted_messages, stream=True)
                    
                    if config.get("PRINT_LOG"):
                    
                       func.log("Streaming response initiated...")
                    completed_response = ""
                    for chunk in raw_output:
                        if chunk:
                            completed_response += str(chunk)
                            payload = {"choices": [{"delta": {"content": str(chunk)}}]}
                            yield f"data: {json.dumps(payload)}\n\n"
                            
                    if config.get("PRINT_LOG"):
                        func.log("Streaming response completed.")
                        brain_hub.add_history_message("assistant", completed_response)
                        brain_hub.save_history_to_json(brain_hub.history_file)
                    yield "data: [DONE]\n\n"

                except Exception as e:
                    print(f"{Color.RED}Streaming Error: {e}{Color.RESET}")
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
            return StreamingResponse(event_generator(), media_type="text/event-stream")
        
        else:
            try:
                if brain_hub.orchestrator.llm is None:
                    raise HTTPException(status_code=503, detail="LLM not initialized.") 
                    
                raw_output = brain_hub.orchestrator.llm.chat(formatted_messages, stream=False)
                
                if isinstance(raw_output, str):
                    response_text = raw_output
                else:
                    response_text = "".join([str(chunk) for chunk in raw_output if chunk])
                    brain_hub.add_history_message("assistant", response_text)
                    brain_hub.save_history_to_json(brain_hub.history_file)
                return {
                    "choices": [{
                        "message": {"role": "assistant", "content": response_text}
                    }]
                }
            except Exception as e:
                print(f"{Color.RED}Inference Error: {e}{Color.RESET}")
                raise HTTPException(status_code=500, detail=str(e))

    return app