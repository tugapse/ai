import threading
from typing import Any, Optional
import uvicorn
from fastapi import FastAPI

import functions as func
from services.history_manager import HistoryManager
from modules.base_module import BaseModule

from .brain_hub import BrainHub
from .app import create_app  

        
class JarvisServerModule(BaseModule):
    """
    A module wrapper for the JARVIS Brain Server.
    Respects the standard JARVIS module lifecycle.
    """
    def __init__(self, host: str = "0.0.0.0", port: int = 8000, **kwargs):
        """
        Args:
            host (str): IP to bind the server to.
            port (int): Port for the API.
        """
        self.host = host
        self.port = port
        self.kwargs = kwargs
        
        self._brain_hub: Optional[BrainHub] = None
        self._fastapi_app: Optional[FastAPI] = None
        self._server_thread: Optional[threading.Thread] = None
        self._uvicorn_server: Optional[uvicorn.Server] = None

    def initialize(self, config: Any, orchestrator: Any, history_manager: HistoryManager):
        """
        Initializes the Server Brain and prepares the FastAPI application.
        
        Args:
            config (ProgramConfig): The global configuration.
            orchestrator (ModelOrchestrator): The existing model manager for the Main PC.
            history_manager (HistoryManager): Optional history manager (not directly used here
                                              but kept for compatibility with existing lifecycle).
        """
        if self._brain_hub:
            func.log("JarvisServerModule is already initialized.", level="WARN")
            return

        func.log(f"Initializing Brain Server on {self.host}:{self.port}...")

        # 1. Initialize the BrainHub wrapper
        self._brain_hub = BrainHub(config)
        self._brain_hub.orchestrator = orchestrator

        # 2. CREATE THE APP: Pass the config object so the endpoints can access state
        self._fastapi_app = create_app(self._brain_hub, config)

        # 3. Setup Uvicorn config
        uvicorn_config = uvicorn.Config(
            app=self._fastapi_app, 
            host=self.host, 
            port=self.port, 
            log_level="info"
        )
        self._uvicorn_server = uvicorn.Server(uvicorn_config)

    def start(self):
        """
        Starts the server in a separate thread so it doesn't block 
        the main Program execution.
        """
        if not self._uvicorn_server:
            func.error("Cannot start server: Not initialized.", level="ERROR")
            return

        func.log(f"Starting Neural Link on http://{self.host}:{self.port}")
        self._server_thread = threading.Thread(target=self._uvicorn_server.run, daemon=True)
        self._server_thread.start()
        self._server_thread.join()

    def get_instance(self) -> Optional[BrainHub]:
        """Returns the active BrainHub instance."""
        return self._brain_hub

    def shutdown(self):
        """Gracefully stops the API and releases model VRAM."""
        func.log("Shutting down Brain Server Module.")
        
        if self._uvicorn_server:
            self._uvicorn_server.should_exit = True
            
        if self._brain_hub:
            self._brain_hub.unload_brain()
            
        self._brain_hub = None
        self._fastapi_app = None