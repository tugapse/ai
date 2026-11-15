# Findings — code issues found while documenting

> Things noticed while writing `guide/` that were **not fixed yet**. To handle in a later session.
> Each item: where, what, and a suggested fix. Mark ✅ when done (and update the guide page that
> mentions it).

Status: ⬜ open · 🟨 decided / in progress · ✅ fixed

---

## Configuration (layer 8) — `guide/08-configuration.md`

| # | Status | Where | Issue | Suggested fix |
|---|--------|-------|-------|---------------|
| C1 | ✅ 2026-11-14 | `services/config_helper.py`, `services/prompt_loader.py` | `--system NAME` and `SYSTEM_PROMPT_FILE` resolved in `system/` instead of `system/system-prompt/`. | Fixed: default folder is now `system/system-prompt/` (`--system chat/default` works, `default` finds `default.md`); an empty `default.md` falls back to the built-in line; the built-in path points at `assets/templates/system/system-prompt/default.md`. Tests: `test_prompt_loader_paths.py` (+ updated `test_config_helper.py`). Guide updated. |
| C2 | ✅ | `assets/templates/system/system-prompt/default.md`, `chat/default.md` | Both files are empty (0 bytes). | Write a real default chat prompt (JARVIS personality), or remove them. ✅ 2026-11-15 — both files hold a short JARVIS chat prompt. The chat prompt now also looks in `user/system-prompt/` first (like agents). |
| C3 | ✅ 2026-11-14 | `config.py` `copy_templates_to_user_dir`, `main.py` help | `--overwrite-config` says "Force configuration and templates overwriting", but templates use `copy_skip_existing` (only missing files are copied) and `config.json` is reset to defaults (user settings lost). | Fixed (help text): `--overwrite-config` now says it resets config.json and copies only missing templates. Refreshing templates is C4. |
| C4 | ✅ | `config.py` | Template updates never reach an existing AI folder: new versions of `system/` files are not copied on upgrade. | Sync `system/` on version change (user files in `user/` stay untouched). ✅ 2026-11-15 — `ai.template_sync`: every start compares shipped `system/` files with the AI folder; untouched copies are replaced, edited ones backed up to `system/backup/<date>/` first. Manifest `system/.templates.json`. `user/` untouched. Tests: `tests/ai/services/test_template_sync.py`. |
| C5 | ✅ 2026-11-14 | `config.py` `ProgramSetting` | Dead settings: `OLLAMA_HOST`, `REMOTE_MODE`, `REMOTE_URL`, `PATHS_TASKS_TEMPLATES`, `PATHS_MODEL_CONFIGS` (written or declared, never read). | Fixed: removed unused settings `OLLAMA_HOST`, `REMOTE_MODE`, `REMOTE_URL`, `PATHS_TASKS_TEMPLATES`, `PATHS_MODEL_CONFIGS`, plus `MODEL_NAME`, `SYSTEM_PROMPT_FOLDER`, `PATHS_CHAT_LOG`. Old keys left in a config.json are harmless. |
| C6 | ✅ | `agents/session_manager.py` | Agent sessions are stored under `system/logs/agents/` — user data inside a logs folder. | Move to `<root>/sessions/agents/` (with migration). ✅ 2026-11-15 — `<root>/sessions/agents/`; folders in `system/logs/agents/` are moved on first use (ones already in the new place are left). |
| C7 | ✅ | `services/config_helper.py` ↔ `direct.py` ↔ `services/ui_orchestrator.py` | Circular import: importing `ai.services.prompt_loader` before other modules fails. | Break the cycle (lazy import or move `ProgramConfig` re-export). ✅ 2026-11-15 — `config_helper` (and the services that imported `ProgramConfig` through it) import from `ai.config`. Every module now imports on its own; the `import ai.program` workarounds were removed from the tests. |
| C8 | ✅ 2026-11-14 | `config.py` | Default AI folder was `<temp>/ai` (lost on reboot). | Now `~/Ai`. May change in the future. |

## Agents (layer 3) — `guide/03-agents.md`

| # | Status | Where | Issue | Suggested fix |
|---|--------|-------|-------|---------------|
| A1 | ✅ 2026-11-14 | `agent_orchestrator.py` `run_loop` | `DONE` target clears the agent's memory and always returns to `MASTER` (hard-coded), not the pipeline's `entry_point`. | Fixed: `DONE` returns to the pipeline's `entry_point`. |
| A2 | ✅ | `agent_orchestrator.py` `MAX_ITERATIONS` | Code default is 100; every shipped pipeline sets 300. | Align (doc says 100 = code default). ✅ 2026-11-15 — code default is 300, like the shipped pipelines. |
| A3 | ✅ 2026-11-14 | `agent.py` `load_pipeline_config` | Agent `prompt_file` is only looked up in `system/system-prompt/` — no `user/` override, unlike models and pipelines. Custom prompts live in `system/` and can be lost on a reset. | Fixed: `DirectoryManager.resolve_prompt_file` checks `user/system-prompt/` then `system/system-prompt/` (pipeline loader and the web pipeline editor). Test: `test_prompt_file_lookup.py`. |
| A4 | ✅ | `session_manager.py` `commit` | Session file is an append-only journal with the **full state** every step → grows fast on long sessions. | Keep only the last N states, or store deltas / compress (there's an unused `compress` flag). ✅ 2026-11-15 — journal keeps the first state + last `KEEP_STATES` (3); each line has `turn`. Old journals are trimmed on the next commit. A real session was 17 MB / 54 states. |
| A5 | ✅ | `agent_orchestrator.py` `SpecialistManager(...)` | Only wired to `generate_doc`, which isn't in any pipeline. Possibly dead code. | Remove or document a real use. ✅ 2026-11-15 — removed (`specialist_manager.py`, the `SPECIALIST` event and its UI handlers): `generate_doc` was never a registered tool, so it could not run. |
| A6 | ✅ | `agent_orchestrator.py` `_prepare_payload` | `plan` / `current_step` have a `FIXME`: the plan is never read from responses. | Implement or remove the fields from the payload. ✅ 2026-11-15 — `plan` (always `[]`) and `current_step` (a count of successful tools) removed from the payload. |
| A7 | ✅ | `agent_orchestrator.py` `_gatekeeper` | "Always" approval is per tool, not per path/command (`TODO` in code). | Remember approvals per tool + path / command prefix. ✅ 2026-11-15 — `agents/approval_scope.py`: "always" covers the same command (program + sub-command) or the same tool in the same folder; commands with shell operators and `enable_mcp_server` are never remembered. The permission box shows what "always" covers. |
| A8 | ✅ 2026-11-14 | `system/config/mcp_config.json`, `tools/mcp_bridge.py` | `auto_allow` in the MCP config is **never read** (checked in layer 4). MCP gateways run without approval unless the server name is added to `HIL_TOOLS`. | Fixed: `"auto_allow": false` now gates that server's gateway (default `true` keeps today's behaviour). Tests in `test_mcp_bridge.py`. |

## Tools (layer 4) — `guide/04-tools.md`

| # | Status | Where | Issue | Suggested fix |
|---|--------|-------|-------|---------------|
| T1 | ✅ 2026-11-14 | `cli_args.py` `_check_nhandle_create_tool` | `--create-tool` writes a loose `@tool` function with no `ToolCategory`. The loader refuses loose tools and raises `ImportError`, so the generated file **breaks every agent run** until fixed. | Fixed: `build_tool_skeleton` generates a category + tool; `tool_base_name` never starts with `_` (such files were skipped by the loader). Test: `tests/ai/tools/test_create_tool_skeleton.py`. |
| T2 | ✅ 2026-11-14 | `system/config/mcp_config.json` | Playwright and GitHub are enabled by default and started (`npx`) on every agent run; GitHub needs a token and fails without it. | Done: shipped MCP servers are disabled; `ai mcp list/enable/disable` for the user, `list_mcp_servers` / `enable_mcp_server` (always asks, optional `remember`) for agents. Note: an existing `~/Ai/system/config/mcp_config.json` keeps its old `enabled: true` (C4) — run `ai mcp disable NAME` or delete that file. |
| T3 | ✅ | `modules/tools_search/tools.py` | `smart_search` shells out to the system `grep` → likely broken on Windows. | Pure-Python fallback (or ripgrep when present). ✅ 2026-11-15 — pure-Python fallback (`_python_grep`, same output format) when `grep` isn't on PATH; tested against real grep. |
| T4 | ✅ 2026-11-14 | `user/config/mcp_config.json` lookup | The user file replaces the system one completely (no merge), so adding one server means copying all of them. | Fixed: `MCPBridge.load_from_configs` merges system then user config by server name. Test in `test_mcp_bridge.py`. |

## Interfaces & program (layers 1–2) — `guide/01-interfaces.md`, `guide/02-program.md`

| # | Status | Where | Issue | Suggested fix |
|---|--------|-------|-------|---------------|
| W1 | ✅ 2026-11-14 | `services/process_manager.py:2` | `import fcntl` at module level (Unix only), and `main.py` imports `ProcessManager` → **startup likely fails on Windows** (since the process registry, v3.7.0). Also `os.getuid()` in `directory_manager.py:226`. | Fixed in code (not run on a real Windows yet): `fcntl` optional, flock only where available; Windows liveness via `OpenProcess` — `os.kill(pid, 0)` would have **terminated** the process there; `os.getuid` guarded. Tests in `test_process_manager.py` simulate no-fcntl / nt. |
| I1 | ✅ 2026-11-14 | `chat/chat.py` `run_command` | Unknown `/command` in plain chat sets `running_command = True` and triggers `EVENT_COMMAND_STARTED`, which nobody listens to (`ChatCommandInterceptor` is never instantiated) → the prompt never comes back. | Fixed: an unhandled `/command` prints "Unknown command" and gives the prompt back. Test in `test_chat.py`. |
| I2 | ✅ 2026-11-14 | `chat/chat.py`, `program.py` `_handle_agent_run_requested` | After `/agent <task>` in plain chat, `running_command` is never reset → prompt stuck. It also uses the legacy `Agent` facade (no user tools, no categories registered), unlike `build_orchestrator`. | Fixed: `/agent` uses `build_orchestrator` (same tools as `--agent`) and always calls `terminate_command()`. Test: `tests/ai/test_program_agent_request.py`. |
| I3 | ✅ 2026-11-14 | `chat/chat_command_interceptor.py` | Dead code: `/save`, `/load`, `/list` are implemented but the class is never used. | Done: `/save NAME`, `/load NAME`, `/list` wired in the plain chat (`<AI folder>/sessions/chat/`); names cannot leave that folder; a missing name shows the usage. |
| I4 | ✅ | `program.py` `load_tool_registry` vs `agents/agent.py` | Plain chat loads user tools from `<root>/tools`, agents from `<root>/user/tools`. Also the chat tool prompt is computed before `allow_tools` is set, so chat never advertises tools (the chat tool path is effectively dead). | One tools folder; decide whether plain chat should have tools at all. ✅ 2026-11-15 — plain chat loads user tools from `user/tools` (same as agents). Decision: the plain chat doesn't offer tools (use `/agent`); the dead tool-prompt code (`allow_tools`) was removed. |
| V1 | ✅ 2026-11-14 | `modules/voice/vibe_module.py`, `assets/voices/` | Code default voice is `pt-Spk1_man`, but the repo ships only English voices (`en-*`); with `VOICE_FILE` unset, `None` is passed and the first voice found is used. README says "including Portuguese". | Done: `pt-Spk1_man.pt` and `pt-Spk0_woman.pt` downloaded from microsoft/VibeVoice `demo/voices/streaming_model` (same source as the shipped `en-Carter_man.pt`, byte-identical; pickle globals checked: only torch/transformers/OrderedDict) into `assets/voices/`; default voice `pt-Spk1_man` when `VOICE_FILE` is unset. |

## Models (layer 6) — `guide/06-models.md`

| # | Status | Where | Issue | Suggested fix |
|---|--------|-------|-------|---------------|
| M1 | ✅ | `services/engine_manager.py` `load_model_instance` | `seq2seq_lm` is a `ModelType` (and accepted by `--model-type`) but has no branch → "Unhandled model_type". `t5_model.py` exists but is never used. | Wire up `T5Model` or remove the type. ✅ 2026-11-15 — wired (`EngineManager._create_seq2seq_lm`). `T5Model` was broken too: the prompt text was always empty (role case mismatch), it tokenised twice, `pull` used undefined names, config `model_properties` were ignored. Tested with `google/flan-t5-small`. |
| M2 | ✅ 2026-11-14 | `engine_manager.py` `is_engine_installed` vs `scripts/install_engines.py` | The installer uses the id `gemini`, the check uses `gemini_api` / `gemini_vertex`; plain `ModelType.GEMINI` isn't mapped, so the check always passes. `jarvis` isn't checked either. | Fixed: `gemini` model type is now checked against the installer's `gemini` id (the installer keeps `gemini_api`/`gemini_vertex` in sync). `jarvis` still unchecked (its deps come with the base install). Test in `test_model_manager.py`. |
| M3 | ✅ 2026-11-14 | `cli_args.py` `--generate-config` | Writes the new config into `system/models/` (can be lost on a reset). | Fixed: `--generate-config` writes to `user/models/`. |
| M4 | ✅ 2026-11-14 | `core/llms/jarvis.py` | Default `base_url` is `http://0.0.0.0:9999` (a listen address, not a reachable one) and default model name `gpt-4o` (copied from the OpenAI client). | Fixed: defaults are `http://127.0.0.1:9999` and model name `default`. |

## Server (layer 7) — `guide/07-server.md`

| # | Status | Where | Issue | Suggested fix |
|---|--------|-------|-------|---------------|
| S1 | ✅ 2026-11-14 | `modules/server/app.py`, `routers/sessions.py`, `routers/prompts.py` | Was: chat, `GET /api/v1/sessions[/…]`, prompts, model-configs and stats answered **any** address. **Fixed:** a middleware now applies `SERVER_TRUSTED_NETWORKS` to every route (test: `test_untrusted_network_is_403_on_every_route`). **Still open (your decision):** reading saved chat sessions only needs a trusted network, not a paired device — `test_reads_stay_open` keeps that on purpose. | Done: trusted networks on every route; chat sessions are tagged with a per-browser `jarvis_client` id — an unpaired browser lists/reads/continues only its own, a paired device sees all, cookie-less clients (CLI, relay) chat as before. Tests: `TestSessionsPerBrowser`, `test_untrusted_network_is_403_on_every_route`. |
| S2 | ✅ | `config` default | `SERVER_HOST` defaults to `0.0.0.0` (all interfaces). | Fine for LAN use, but document it next to S1, or default to the LAN interface. ✅ 2026-11-15 — kept `0.0.0.0` (phones/tablets on the LAN); documented in guide 07 (Security) and 08, with `127.0.0.1` for local-only. |

## Other

| # | Status | Where | Issue | Suggested fix |
|---|--------|-------|-------|---------------|
| L1 | ✅ 2026-11-14 | `main.py` `hack_warnings` | Every start with transformers/sentence-transformers installed (e.g. `--build-knowledge`) printed torch's warning "`<enum 'KernelPreference'>` is an Enum subclass … `register_constant()` … deprecated" — triggered by `torchao`, not by JARVIS. | Fixed: a logging filter on `torch.utils._pytree` drops that one message (a filter, since torch may reset logger levels). Verified by importing `torchao` after `hack_warnings()`. |

## CLI (found during the sub-command refactor)

| # | Status | Where | Issue | Suggested fix |
|---|--------|-------|-------|---------------|
| X1 | ✅ 2026-11-14 | `cli_args.py` `_is_list_models` | `--list-models` was never implemented: it printed "Not available at the moment" (`FIXME`). | Implemented `ai models list` (`ai/cli/models.py`): user then system configs, type and model name, configs hidden by a user one marked. |
| X2 | ✅ 2026-11-14 | `main.py` `maintenance_keys` | `--list-sessions` loaded the model before listing sessions. | `list_sessions` added to the maintenance keys. |

## README / project

| # | Status | Where | Issue | Suggested fix |
|---|--------|-------|-------|---------------|
| P1 | ✅ | `pyproject.toml` | `requires-python = ">=3.8, <3.14"` isn't realistic (developed on 3.13). | Set the real minimum. ✅ 2026-11-15 — `>=3.10, <3.14` (the code uses `X | None` annotations and `str.removeprefix`). Badge and install guide say 3.10–3.13. |
| P2 | ✅ | release task / workflow | README version badge is updated by hand. | Bump it in the release step. ✅ 2026-11-15 — README badge reads `project.version` from `pyproject.toml` on `master` (shields.io dynamic badge). |
| P3 | ✅ | repo root | Empty folders `docs-min/`, `docs-mini/`, `docss/`; build notes in `TODO`. | Delete folders; move notes to the installation guide. ✅ 2026-11-15 — the empty folders were already gone; `TODO` deleted (its notes are in guide 09). |
| P4 | ⬜ | `.github/workflows` | No test CI (only package publishing). | Decide if worth adding. |
