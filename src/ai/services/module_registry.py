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
            "vector_memory": self._load_vector_memory_logic
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


    def unload_module(self, name: str):
        """Safely unloads a single module and frees its resources."""
        if name not in self._active_modules:
            return

        instance = self._active_modules[name]
        func.log(f"ModuleRegistry: Unloading '{name}'...")
        
        try:
            if hasattr(instance, 'unload'):
                instance.unload()
            elif hasattr(instance, 'shutdown'):
                instance.shutdown()
            
            if hasattr(instance, 'thread') and instance.thread and instance.thread.is_alive():
                instance.thread.join(timeout=2.0)
                
            del self._active_modules[name]
            
        except Exception as e:
            func.error(f"ModuleRegistry: Error unloading '{name}': {e}", level="ERROR")


    def unload_all(self):
        """Cleanly unloads all active modules."""
        func.log("ModuleRegistry: Initiating global shutdown sequence...")
        
        active_names = list(self._active_modules.keys())
        
        for name in active_names:
            self.unload_module(name)
            
        func.log("ModuleRegistry: All modules safely unloaded.")

    def shutdown(self):
        """Alias for unload_all to maintain compatibility with existing shutdown calls."""
        self.unload_all()