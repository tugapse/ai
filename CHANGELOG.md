# Changelog

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