from typing import Dict, Any, Optional
from entities.model_enums import EngineType
from services.model_manager import EngineManager
from config import ProgramConfig, ProgramSetting
import functions as func

class ModuleRegistry:
    """
    Plugin Manager for JARVIS modules.
    Supports dynamic loading/unloading and dictionary-style access.
    """
    def __init__(self, config: ProgramConfig):
        self.config = config
        self._active_modules: Dict[str, Any] = {}
        
        # Manifest of available module loaders
        self._manifest = {
            "voice": self._load_voice_logic,
            "vector_memory": self._load_vector_memory_logic,
            "server_hub": self._load_server_logic,   # NEW: Neural Hub Logic
            "client_link": self._load_client_logic,   # NEW: Neural Link Logic
        }

    def __getitem__(self, key: str) -> Optional[Any]:
        """Allows the prog.modules['voice'] syntax."""
        return self._active_modules.get(key)

    def load_all(self):
        """Loads all modules specified as enabled in the configuration."""
        for mod_name, loader_func in self._manifest.items():
            config_key = f"{mod_name.upper()}_ENABLED"
            
            if self.config.get(config_key, False):
                func.log(f"ModuleRegistry: Booting '{mod_name}'...")
                instance = loader_func()
                if instance:
                    self._active_modules[mod_name] = instance
            else:
                func.debug(f"ModuleRegistry: Skipping '{mod_name}' (Not requested).")


    def _load_server_logic(self):
        """Initializes the Brain Server module for the Main PC."""
        host = self.config.get("SERVER_HOST", "0.0.0.0")
        port = self.config.get("SERVER_PORT", 8000)

        try:
            from modules.server.server_module import JarvisServerModule
            server_module = JarvisServerModule(host=host, port=port)
            func.log(f"ServerModule loaded. Target: {host}:{port}")
            return server_module
        except ImportError as e:
            func.error(f"Failed to import ServerModule. Error: {e}")
            return None

    def _load_client_logic(self):
        """Initializes the Remote Connector module for the Tiny PC."""
        remote_url = self.config.get("REMOTE_BRAIN_URL")
        preferred_model = self.config.get("MODEL_CONFIG_NAME", "default")

        if not remote_url:
            func.error("Client module enabled but REMOTE_BRAIN_URL is missing in config.", level="ERROR")
            return None

        try:
            from modules.client.remote_module import RemoteConnectorModule
            client_module = RemoteConnectorModule(url=remote_url, model_id=preferred_model)
            func.log(f"ClientModule loaded. Linked to: {remote_url}")
            return client_module
        except ImportError as e:
            func.error(f"Failed to import RemoteConnectorModule. Error: {e}")
            return None

    def _load_voice_logic(self):
        """The specific steps to boot VibeVoice."""
        if not EngineManager.is_engine_installed(EngineType.VOICE_ENGINE):
            func.log("Voice Engine not found. Run --install.", level="ERROR")
            return None
            
        from modules.voice.vibe_module import VibeVoiceModule
        voice = VibeVoiceModule() 
        voice.preload() 
        return voice

    def _load_vector_memory_logic(self):
        """Boots the VectorMemoryModule wrapper."""
        if not EngineManager.is_engine_installed(EngineType.VECTOR_MEMORY):
            func.log("Vector Memory module not found. Run --install.", level="ERROR")
            return None

        db_path = self.config.get("VECTOR_DB_PATH") or func.get_root_directory() + "/databases"
        
        kwargs = {
            "recency_weight": self.config.get("VECTOR_RECENCY_WEIGHT", 1.0),
            "importance_weight": self.config.get("VECTOR_IMPORTANCE_WEIGHT", 1.0),
            "relevance_weight": self.config.get("VECTOR_RELEVANCE_WEIGHT", 1.0),
        }

        try:
            from modules.memory.vector_memory_module import VectorMemoryModule
            memory_module = VectorMemoryModule(db_path=db_path, **kwargs)
            func.log("VectorMemoryModule loaded (pending initialization).")
            return memory_module
        except ImportError as e:
            func.error(f"Failed to import VectorMemoryModule. Error: {e}", level="ERROR")
            return None

    def shutdown(self):
        """Cleanly closes everything on exit."""
        active_names = list(self._active_modules.keys())
        for name in active_names:
            self.unload_module(name)