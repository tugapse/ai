from typing import Dict, Any, Optional
from ai.entities.model_enums import EngineType
from ai.modules.base_module import BaseModule
from ai.services.engine_manager import EngineManager
from ai.services.config_helper import ProgramConfig, ProgramSetting
import ai.functions as func

class ModuleRegistry:
    """
    Plugin Manager for JARVIS modules.
    Supports dynamic loading/unloading and dictionary-style access.
    """

    TOOL_MODULES = ("tools_filesystem", "tools_search", "tools_shell", "tools_web", "tools_notify")

    def __init__(self, config: ProgramConfig):
        """
        Initializes the ModuleRegistry.

        Args:
            config: The global program configuration object containing settings.
        """
        self.config = config
        self._active_modules: Dict[str, BaseModule] = {}
        
        # Manifest of available module loaders
        self._manifest = {
            "voice": self._load_voice_logic,
            "vector_memory": self._load_vector_memory_logic,
            "knowledge_graph": self._load_knowledge_graph_logic
        }

        # Built-in agent tool modules (ai.modules.tools_*). Enabled unless the config
        # explicitly sets "<NAME>_ENABLED": false.
        self._enabled_by_default = set()
        for name in self.TOOL_MODULES:
            self._manifest[name] = (lambda n=name: self._load_tool_module(n))
            self._enabled_by_default.add(name)

    def __getitem__(self, key: str) -> Optional[BaseModule]:
        """
        Allows the prog.modules['voice'] syntax to retrieve an active module.

        Args:
            key: The name of the module to retrieve.

        Returns:
            The BaseModule instance if found, otherwise None.
        """
        return self._active_modules.get(key)
    
    def items(self):
        """
        Returns a view of all currently active modules and their names.

        Returns:
            A tuple of (module_name, BaseModule) pairs.
        """
        return self._active_modules.items()

    def load_all(self):
        """
        Loads all modules specified as enabled in the configuration.

        It iterates through the manifest, checks the configuration for the
        corresponding ENABLED flag, and instantiates the module if enabled.
        """
        for mod_name, loader_func in self._manifest.items():
            config_key = f"{mod_name.upper()}_ENABLED" 

            # Determine whether to load this module
            enabled_value = None
            try:
                enabled_value = self.config.get(config_key, None)
            except Exception:
                enabled_value = None


            if enabled_value is None:
                should_load = mod_name in self._enabled_by_default
            else:
                should_load = enabled_value if isinstance(enabled_value, bool) else str(enabled_value).strip().lower() in ("1", "true", "yes", "on")

            if should_load:
                func.log(f"ModuleRegistry: Booting '{mod_name}'...")
                instance = loader_func()
                if instance:
                    self._active_modules[mod_name] = instance
            else:
                func.debug(f"ModuleRegistry: Skipping '{mod_name}' (Not requested).")

    def _load_tool_module(self, name: str):
        """
        Imports ai.modules.<name> and builds its ToolModule via create_module().

        Returns:
            The initialized ToolModule, or None if it cannot be loaded.
        """
        try:
            import importlib
            module = importlib.import_module(f"ai.modules.{name}").create_module()
            module.initialize()
            return module
        except Exception as e:
            func.error(f"ModuleRegistry: failed to load tool module '{name}': {e}")
            return None

    def tool_functions(self) -> Dict[str, Any]:
        """All tools exposed by the active tool modules: {tool_name: callable}."""
        from ai.modules.base_module import ToolModule
        tools: Dict[str, Any] = {}
        for name, mod in self._active_modules.items():
            if not isinstance(mod, ToolModule):
                continue
            try:
                instance = mod.get_instance()
            except Exception:
                continue
            provider = getattr(instance, "tools", None)
            if provider is not None and hasattr(provider, "get_tools"):
                tools.update(provider.get_tools())
        return tools

    def _load_voice_logic(self):
        """
        The specific steps to boot VibeVoice.

        Checks for the Voice Engine installation. If present, it instantiates
        VibeVoiceModule using configuration settings and calls preload().

        Returns:
            The initialized VibeVoiceModule instance, or None if the engine is missing.
        """
        if not EngineManager.is_engine_installed(EngineType.VOICE_ENGINE):
            func.log("Voice Engine not found. Run --install.", level="ERROR")
            return None
            
        from ai.modules.voice.vibe_module import VibeVoiceModule
        voice = VibeVoiceModule( voice_file=self.config.get(ProgramSetting.VOICE_FILE), volume=1.5) 
        voice.preload() 
        return voice

    def _load_vector_memory_logic(self):
        """
        Boots the VectorMemoryModule wrapper.

        Checks for the Vector Memory engine. If found, it constructs the module
        using paths and weights derived from the configuration.

        Returns:
            The initialized VectorMemoryModule instance, or None if the engine is missing or import fails.
        """
        if not EngineManager.is_engine_installed(EngineType.VECTOR_MEMORY):
            func.log("Vector Memory module not found. Run --install.", level="ERROR")
            return None

        db_path = self.config.get(ProgramSetting.VECTOR_DB_PATH) or func.get_root_directory() + "/databases"
        
        kwargs = {
            "recency_weight": self.config.get(ProgramSetting.VECTOR_RECENCY_WEIGHT, 1.0),
            "importance_weight": self.config.get(ProgramSetting.VECTOR_IMPORTANCE_WEIGHT, 1.0),
            "relevance_weight": self.config.get(ProgramSetting.VECTOR_RELEVANCE_WEIGHT, 1.0),
        }

        try:
            from ai.modules.vector_memory.vector_memory_module import VectorMemoryModule
            memory_module = VectorMemoryModule(db_path=db_path, **kwargs)
            func.log("VectorMemoryModule loaded (pending initialization).")
            return memory_module
        except ImportError as e:
            func.error(f"Failed to import VectorMemoryModule. Error: {e}", level="ERROR")
            return None

    def _load_knowledge_graph_logic(self):
        """
        Boots the KnowledgeGraph module wrapper.

        Imports and instantiates the KnowledgeGraph. It attempts to call preload()
        and then attempts to register the graph with the orchestrator if the
        method exists, handling potential integration errors gracefully.

        Returns:
            The initialized KnowledgeGraph instance, or None if loading fails.
        """
        try:
            from ai.modules.knowledge_graph import KnowledgeGraph
            kg = KnowledgeGraph()
            if hasattr(kg, "preload"):
                kg.preload()
            # Auto-wire Knowledge Graph integration with orchestrator if available, else bootstrap module-level
            try:
                if hasattr(kg, "register_with_orchestrator"):
                    kg.register_with_orchestrator()
                else:
                    from ai.modules.knowledge_graph import register_with_orchestrator as _kg_reg
                    _kg_reg()
            except Exception as _e:
                func.debug(f"KG integration hook failed: {_e}")
            func.log("KnowledgeGraphModule loaded.")
            return kg
        except Exception as e:
            func.error(f"Failed to import KnowledgeGraphModule. Error: {e}", level="ERROR")
            return None

    def unload_module(self, name: str):
        """
        Safely unloads a single module and frees its resources.

        It checks for 'unload' or 'shutdown' methods on the instance, attempts
        to join any associated thread, and then removes the module from the active registry.

        Args:
            name: The name of the module to unload.
        """
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
        """
        Cleanly unloads all active modules.

        Iterates over a copy of the active module keys and calls unload_module
        for each one to ensure a controlled shutdown sequence.
        """
        func.log("ModuleRegistry: Initiating global shutdown sequence...")
        
        active_names = list(self._active_modules.keys())
        
        for name in active_names:
            self.unload_module(name)
            
        func.log("ModuleRegistry: All modules safely unloaded.")

    def shutdown(self):
        """
        Alias for unload_all to maintain compatibility with existing shutdown calls.

        Initiates the global shutdown sequence for all registered modules.
        """
        self.unload_all()