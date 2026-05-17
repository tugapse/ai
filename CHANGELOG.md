# Changelog

## v3.1.3

### [Added]
- feat(ai-project-documentation): Add script to generate project documentation.
- feat(knowledge_graph): Integrate KnowledgeGraph with orchestrator surface.
- feat(tools): Add dynamic user tool loader and tool skeleton generation.
- feat(server): Add model-configs endpoint to list model configurations.
- feat(prompt_manager): Add aliases for prompt management (read, create, update).
- feat: Enhance chat service with improved session routing and system prompt handling.
- feat: Add prompt management endpoints and schemas.
- feat: Implement agent architecture with event handling and agent mode in chat.
- test(tests): Add extensive test suite, tooling, and fixtures.
- Add base CSS styles for dark and light themes.

### [Changed]
- refactor(tests): Align imports to the new ai.* package layout.
- refactor(ai): Rename `ensure_list` and update call sites.
- Make prefix command completion consider leading slash.

## v3.1.1

### [Fixed]
- fix(engine): Update vertex AI parameter retrieval in Gemini model instantiation

### [Changed]
- Refactor(config): Remove config.json and update ProgramSetting for improved clarity and organization
- Refactor(core/config): Centralize CLI config handling and lazy LLM init

### [Added]
- add FE build to be served by the fast api server

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

## v2.2.0

- and update logic * Renamed `CLEAR_CONSOLE` to `ALLOW_CLEAR_CONSOLE` for clarity and consistency with new configuration semantics. * Updated all references to use the new variable name, aligning behavior with argument-based control logic. * This change centralizes console-clearing decision-making through `func.ALLOW_CLEAR_CONSOLE`, improving configurability.
- refactor: Remove --model-name requirement for --generate-config and introduce model-type-specific config defaults - Updated `cli_args.py` to remove validation for --model-name when using --generate-config. - Removed --model-name argument from `main.py`'s config group, as it's no longer required. - Refactored `model_config_manager.py` to generate model-specific default configs based on type (OLLAMA, CAUSAL_LM, GGUF) instead of a unified default. - Eliminated the command-line interface for generating configs, now handled via model-type-driven logic. - Simplified config creation by replacing generic defaults with per-model-type tailored properties.
- feat: Enhance Direct AI Module with Session Management and Handler Integration
- chore: Update documentation and code to improve clarity and consistency.
- feat: Add GPU acceleration support and enhance logging Support Vulkan and CUDA configurations with environment variables and device detection. Added GPU-specific methods for cache management and refined log file naming sanitation. This enables hardware-accelerated inference while improving system reliability.
- Merge branch 'develop' of https://github.com/tugapse/ai into develop
- feat: Add GPU inference support and parameter configuration across models
- feat: Add GPU inference support and parameter configuration across models
- Merge branch 'develop' of https://github.com/tugapse/ai into develop
- Merge tag 'hotfix-20250715' into develop
- Merge branch 'hotfix/hotfix-20250717'
- fix windows paths
- fix: Add ERROR level logging and fix token buffer return in think parser
- Merge tag 'release-20250713' into develop

## v2.1.0

- orrected function name from get_formated_text to get_formatted_text in functions.py. Added short aliases -pl and -pdb for --print-log and --print-debug in main.py. Modified output handling to include newline after \r and stripped whitespace from token buffer in think_parser.py.
- refactor: Use shared formatted text function for logging and update command-line arg default Move color-coding logic to helper function for consistent formatting across log, debug, and out. Add get_formated_text() to centralize styling based on level. Update --msg argument default to None for configuration flexibility. * Refactored log(), debug(), and out() to use get_formated_text() for consistent color-coding. * Added get_formated_text() to handle COLOR-based formatting per level (ERROR, WARNING, DEBUG). * Changed --msg argument default from "hello :)" to None to allow optional input. * Improved maintainability by centralizing styling logic. * Ensures logging and output respects PRINT_LOG/PRINT_DEBUG settings.
- feat: Add functions module and update logging utility fix: Change logging level from CRITICAL to ERROR refactor: Update thinking animation handler docs: Add .vscode/* to .gitignore and delete launch.json
- feat: Add ProgramSetting import and remove log level parameters
- feat: Add configuration support and improve logging consistency
- Merge tag 'hotfix-20250713_1' into develop
- Merge branch 'hotfix/hotfix-20250713_1'
- chore: Bump version to 2.0.1
- fix: Handle Windows path escaping and safe default for template injections This change addresses two issues: * Escapes backslashes in paths to ensure compatibility with Windows systems by replacing "\\\\" with "\\\\\\\\". * Adds a default empty list for "INJECT_TEMPLATES" to prevent AttributeError when the key is missing. Both updates improve reliability and cross-platform functionality.
- perf: Ensure pip is up-to-date before installing dependencies
- Merge tag 'hotfix-20250712_1' into develop
- Merge tag 'release-20250712_1' into develop

## v2.0.0

- Merge branch 'hotfix/hotfix-20250712_1'
- refactor: Remove empty lines after method definitions for cleaner code structure
- Merge branch 'release/release-20250712_1'
- feat: Add frequency_penalty parameter and update model parameter handling
- feat: Update configuration and logging settings for enhanced debug and print options
- Move files around
- move code into src/ai folder
- feat: Add build script and dependency installer for LLM models
- added tests
- feat: Update Qwen3-HF model configuration parameters
- Merge branch 'master' of https://github.com/tugapse/ai into develop
- Merge tag 'hotfix-20250711' into develop
- Merge tag 'release-20250711_1' into develop

## v1.5.0

- nditional logic based on the JSON config
- Add new readme.md
- Fix: Ensure alternating roles in chat messages
- remove unused file
- Below is an explanation of what this patch does:
- changed bash ans cmd files
- temp
- The provided code snippets show changes made to a Python project that interacts with an AI language model (OllamaModel). Here's a summary of the modifications:
- Below is an overview of whats been changed and why:
- remove cache
- huggingface working, kind of....
- Add model Params to program file
- add image parameter
- Extract logic to base class from ollama model
- test in windows
- temp commit
- renamed init to main and added .gitignore
- renamed init to main and added .gitignore
- changed bash ans cmd files
- changed bash ans cmd files
- Merge tag 'hoyfix-20250612' into develop
- **cli_args.py:** 1. Imports have been updated to include `ProgramSetting`. 2. The order of some checks has been slightly rearranged. 3. Hard-coded paths in the code have been replaced with references to `ProgramConfig.get_current().config` and `ProgramSetting` constants.
- updated templates
- fix system templates key
- fix if no user config is provided
- Merge user config insted of replace
- add strip
- add terminal pipe
- fix config paths
- Add --no-log, --no-out
- fix output filename argument
- fix images
- fix images in direct ask
- revert to default config and Ollama impl
- huggingface working, kind of....
- update model settings
- add union typing
- Add model Params to program file
- add image parameter
- Extract logic to base class from ollama model
- add image|images to cli argument and load filename into chat images
- change ollama default endpoint
- rename sh file
- fix load files
- test in windows
- temp commit
- update requirements.txt
- temp
- feat: Add control role and improve thinking animation handler
- The provided code snippets show changes made to a Python project that interacts with an AI language model (OllamaModel). Here's a summary of the modifications:
