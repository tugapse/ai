from typing import Optional, Any
import functions as func
from core.modules.base_module import BaseModule
from core.llms.remote_connector import RemoteBrainConnector

class RemoteConnectorModule(BaseModule):
    """
    The 'Neural Link' module for the Client (Tiny PC).
    Wraps the RemoteBrainConnector to provide access to the Main PC's Brain.
    """
    def __init__(self, url: str, model_id: str = "default", **kwargs):
        """
        Args:
            url (str): The base URL of the JARVIS Server (e.g., http://0.0.0.0:8000)
            model_id (str): The preferred model config to request from the server.
        """
        super().__init__(module_name="RemoteBrainLink", **kwargs)
        self.url = url
        self.model_id = model_id

    def initialize(self, system_prompt: Optional[str] = None):
        """
        Establishes the connection logic. 
        Note: The actual network handshake happens during the first chat() call.
        """
        super().initialize()
        
        func.log(f"Linking to Remote Brain at {self.url} (Model: {self.model_id})")
        
        # Instantiate the actual connector
        self._instance = RemoteBrainConnector(
            url=self.url,
            model_id=self.model_id,
            system_prompt=system_prompt,
            **self.kwargs
        )

    def shutdown(self):
        """Signals the remote brain to stop any active generation before closing."""
        if self._instance:
            func.log("RemoteLink: Closing connection...")
            self._instance.request_shutdown()
        super().shutdown()