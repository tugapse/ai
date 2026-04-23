# Changelog

## v3.1.0

### [Added]
- feat(server): Improve shutdown flow and add frontend assets.
- feat(core,server,kg): Implement knowledge graph and structured LLM output.
- feat(server): Implement comprehensive session management API.
- feat(server): Introduce server watchdog and dynamic sessions.
- feat(llm-server): Implement robust model unloading and server architecture.

### [Changed]
- feat(llm_connector): Use ResponseParser for LLM responses.
- refactor(core): Enhance persistence and model configuration, including session state hydration and support for larger context windows.
- Changed default application path.

## v3.0.0

### [Added]
- feat(agent): Implement advanced file search and local LLM caching
- feat: Introduce `SpeechBridge` for enhanced voice output and agent personas
- Implement VibeVoiceEngine for real-time text-to-speech generation and playback.
- Integrate VibeVoiceEngine into the main program for streaming audio output.
- Add VOICE_ENGINE to EngineType enum and engine registry.

### [Changed]
- Refactor LLMConnector to use XML for structured agent communication.
- Implement tolerant XML parsing with auto-repair for LLM responses.
- Update `_execute_llm_call` to use unique temporary files for output capture.
- Standardize agent prompt templates to enforce XML output format.
- refactor(voice): Decouple voice engine into modular base and VibeVoice
- Update install_engines.py to support VibeVoice installation with specific notes.
- Enhance program startup with _load_modules for optional engine initialization.
- Improve KeyboardInterrupt handling to abort active voice output.
- Refactor shared dependency uninstallation logic in install_engines.py.
- Add vertex_ai property to gemini-25-pro model configuration.

### [Documentation]
- docs(llms): Update direct.py description and Gemini model config
- update docs
- add documentation