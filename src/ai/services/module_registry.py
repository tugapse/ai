from typing import Dict, Any, Optional
from entities.model_enums import EngineType
from services.model_manager import ModelManager
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
            "voice": self._load_voice_logic
        }

    def __getitem__(self, key: str) -> Optional[Any]:
        """Allows the prog.modules['voice'] syntax."""
        return self._active_modules.get(key)

    def load_all(self):
        # The manifest tells the registry what modules are available to be loaded
        manifest = {
            "voice": self._load_voice_logic
        }

        for mod_name, loader_func in manifest.items():
            config_key = f"{mod_name.upper()}_ENABLED"
            
            # Check the config object passed during __init__
            if self.config.get(config_key, False):
                func.log(f"ModuleRegistry: Booting '{mod_name}'...")
                instance = loader_func()
                if instance:
                    self._active_modules[mod_name] = instance
            else:
                # This is what you were seeing before
                func.log(f"ModuleRegistry: Skipping '{mod_name}' (Not requested).", level="DEBUG")


    def load_module(self, name: str) -> Optional[Any]:
        """Public API to dynamically turn on a module."""
        if name in self._active_modules:
            return self._active_modules[name]

        if name not in self._manifest:
            func.log(f"ModuleRegistry: Unknown module '{name}'", level="ERROR")
            return None

        try:
            instance = self._manifest[name]()
            if instance:
                self._active_modules[name] = instance
                self.config.set(f"{name.upper()}_ENABLED", True)
                func.log(f"ModuleRegistry: Module '{name}' is now ONLINE.")
                return instance
        except Exception as e:
            func.log(f"ModuleRegistry: Error loading '{name}': {e}", level="ERROR")
        return None

    def unload_module(self, name: str):
        """Public API to turn off a module and free resources."""
        if name not in self._active_modules:
            return

        instance = self._active_modules[name]
        if hasattr(instance, 'shutdown'):
            try:
                instance.shutdown()
            except:
                pass

        del self._active_modules[name]
        self.config.set(f"{name.upper()}_ENABLED", False)
        func.log(f"ModuleRegistry: Module '{name}' is now OFFLINE.")

    def _load_voice_logic(self):
        """The specific steps to boot VibeVoice."""
        if not ModelManager.is_engine_installed(EngineType.VOICE_ENGINE):
            func.log("Voice Engine not found. Run --install.", level="ERROR")
            return None
            
        from modules.voice.vibe_module import VibeVoiceModule
        voice = VibeVoiceModule() 
        voice.preload() 
        return voice

    def get_voice(self):
        """Legacy support for existing code."""
        return self._active_modules.get('voice')

    def shutdown(self):
        """Cleanly closes everything on exit."""
        active_names = list(self._active_modules.keys())
        for name in active_names:
            self.unload_module(name)