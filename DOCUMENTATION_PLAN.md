# Documentation Plan — JARVIS AI

> Working document. Last update: 2026-11-15 (base: `develop` @ `bcec64e`, version 3.8.1).
> Companion files: [`FINDINGS.md`](FINDINGS.md) (code issues to fix later) and [`guide/`](guide/index.md).

Status: ⬜ to do · 🟨 written, to review · ✅ done

---

## 1. Where we are

### Guide pages (`guide/`)

| # | Page | Status | Notes |
|---|------|--------|-------|
| — | [index.md](guide/index.md) | 🟨 | Layer diagram, page list, other docs in the repo. |
| 1 | [Interfaces](guide/01-interfaces.md) | 🟨 | One-shot CLI, chat, agent chat, one-shot agent, web UI, voice. |
| 2 | [Program](guide/02-program.md) | 🟨 | Startup flow, modes, modules, events, process registry, services. |
| 3 | [Agents](guide/03-agents.md) | 🟨 | Loop, XML format, pipelines, approvals, payload, guards, sessions. |
| 4 | [Tools](guide/04-tools.md) | 🟨 | Categories, every built-in tool, safety, MCP, writing your own. |
| 5 | [Knowledge & memory](guide/05-knowledge-memory.md) | 🟨 | Building knowledge, registry, injection, LTM types/scopes/reflection. |
| 6 | [Models](guide/06-models.md) | 🟨 | Providers, config format, provider details, GPU advisor. "Which model for what" table is **empty, for you to fill**. |
| 7 | [Server](guide/07-server.md) | 🟨 | Ways to use it, relay, security (incl. what's unprotected), web UI, web agents, API. |
| 8 | [Configuration](guide/08-configuration.md) | 🟨 | AI folder, template copying, lookup order, system prompts, tasks, full settings reference, known quirks. |
| 9 | [Installation](guide/09-installation.md) | 🟨 | Linux, engines, GPU builds, Windows/exe, package index, updating, troubleshooting. |
| 10 | [Development](guide/10-development.md) | 🟨 | Code map, tests, conventions, releases, generated docs, utilities. |

All internal links and anchors were checked by script.

### README

| Item | Status |
|------|--------|
| Rewritten in English, honest tone (why / what it does / status / what's next) | ✅ |
| Factual fixes R1–R10 (version, flags, providers, broken links, fake task names…) | ✅ |
| Small changes you want to make yourself | ⬜ (you) |
| Link to `guide/` pages now that they exist | ⬜ |
| Move the long parts (CLI reference, Knowledge, Server) out to the guide, keep a short README | ⬜ |
| "including Portuguese" voice claim — Portuguese voices now ship (FINDINGS V1) | ✅ |

### Code changes made during the docs work

| Change | Tests |
|--------|-------|
| Default AI folder `<temp>/ai` → `~/Ai` (`config.py`) | full suite ✅ |
| System prompts resolve in `system/system-prompt/` (`config_helper.py`, `prompt_loader.py`) — FINDINGS C1 | full suite ✅ (897 passed) + new `tests/ai/services/test_prompt_loader_paths.py` |
| Bug-fix round (2026-11-14): T1, W1, S1 (partly), I1, I2, A8, T4, A1, A3, C3, C5, M2, M3, M4, L1 — details in `FINDINGS.md` | new/updated tests per fix; full suite at the end |
| CLI split into sub-commands (`ai agent`, `ai server`, `ai knowledge build`…), one file per group in `src/ai/cli/` (parser + handlers); old flags still work with a notice. README CLI reference, guide pages, messages and `jarvis.sh` updated. Also X1 (`models list` implemented), X2 | new `tests/ai/test_cli.py` (old vs new forms), smoke-tested every command with `./run.sh` |
| 2026-11-15: C4 (system templates kept up to date, edited files backed up), M1 (`seq2seq_lm` wired, `T5Model` fixed), A4 (session journal capped), A7 ("always" per command / folder) | new `test_template_sync.py`, `test_approval_scope.py`, tests in `test_session_manager.py` / `test_model_manager.py`; full suite |
| 2026-11-15: C2 (JARVIS chat prompt, `user/system-prompt/` override), C6 (sessions → `sessions/agents/`, moved automatically), C7 (import cycle gone), A2, A5 (dead specialist code removed), A6, I4, T3 (Python grep fallback), S2 (documented), P1, P2 (dynamic badge), P3; README links to the guide, `docs/README.md` | new `test_python_grep.py`, tests in `test_session_manager.py`, `test_prompt_loader_paths.py`; full suite 980 passed; CLI smoke test |

Nothing is committed yet.

---

## 2. What's left

### Docs

1. 🟨 **Review the guide pages** (you, in progress). They were written from the code; check tone and
   anything that doesn't match how you actually use JARVIS.
2. ⬜ **Fill "Which model for what"** in `guide/06-models.md` with your notes per model.
3. ✅ **README**: links the guide and is short (274 → 185 lines): the Agents / Knowledge / Server
   sections became "A quick tour" with links, and the full CLI reference moved to
   [Interfaces › Command-line reference](guide/01-interfaces.md#command-line-reference).
4. ⬜ Decide whether to **generate** reference pages from code so they can't drift
   (`guide/reference/cli.md` from argparse, `settings.md` from `ProgramSetting`, `api.md` from
   FastAPI's OpenAPI). Today these live by hand in the README / page 8 / page 7.
5. ✅ `docs/README.md`: says `docs/` is the knowledge viewer and how to serve it.
6. ⬜ Optional "History" page from the timeline below.
7. ✅ "Known issues / quirks" notes in the guide updated after the fixes.

### Repo cleanup

8. ✅ Empty `docs-min/`, `docs-mini/`, `docss/` — already gone.
9. ✅ `TODO` deleted (its GPU build notes are in `guide/09-installation.md`).
10. ⬜ Decide which generated-docs folder is official: `_docs/` (tracked) vs `.docs/` and `.Agents/docs` (ignored).
11. ⬜ Regenerate `_docs/` / `_knowledge/` for the new `ai.modules.knowledge` (`./run.sh knowledge build src --mode diff:master`; uses your model, so run it yourself).

### Code (see `FINDINGS.md` for details and suggested fixes)

Fixed so far: T1, W1 (code; untested on real Windows), S1, T2, I1, I2, I3, V1, A8, T4, A1, A3, C3,
C5, M2, M3, M4, L1, X1, X2, C4, M1, A4, A7, C2, C6, C7, A2, A5, A6, I4, T3, S2, P1, P2, P3. Still open:

| Priority | IDs | Why |
|----------|-----|-----|
| Decision | P4 (test CI) | Your call: GitHub Actions minutes, and which optional deps the runner installs. |
| Check | W1 and T3 on a real Windows machine | Fixed blind / tested only on Linux. |

---

## 3. Background

### Layers

```
 ┌────────────────────────────────────────────────────────────────┐
 │ 1. Interfaces      CLI · Chat · Agent Chat (TUI) · Web · Voice  │
 │ 2. Program         main · cli_args · program · services/*       │
 │ 3. Agents          orchestrator · pipelines · parser · guards   │
 │ 4. Tools  ·  5. Knowledge & Memory                              │
 │ 6. Models (LLM)    Ollama · GGUF · HF · OpenAI · Gemini · Jarvis │
 │ 7. Server          Brain Server · Relay · API · Auth · Frontend │
 │ 8. Configuration · 9. Installation · 10. Development            │
 └────────────────────────────────────────────────────────────────┘
```

### Tone and identity (agreed)

A personal pet project, built out of passion, inspired by JARVIS from Iron Man: an assistant that
runs on my machine, with my models, and can do things for me. One maintainer, not a product or a
framework. README and guide are in English, first person in the README, plain and precise in the
guide. The agents' own system prompts keep their grand "Sentinel Architect" tone — that's JARVIS's
personality, not marketing.

Answers from the maintainer (2026-11-14): web UI used on phone and tablet; uses as many models as
possible (each is better at something); next focus is stability + quality-of-life; no special
story — it's an idea I like. The package index is public.

### Project history (from `git log`, 621 commits)

| Period | What happened |
|--------|---------------|
| Apr–Jun 2024 | First commit 2024-04-30. A small CLI to talk to Ollama: config, `--file`, tasks (the first one commented PHP code), multiline chat, `--output-file`, remote Ollama. ~130 commits in two months. |
| May–Aug 2025 | User config merged instead of replaced, terminal pipes, images, Hugging Face ("working, kind of…"), Windows. |
| Mar 2026 | Agents: multi-agent orchestration, `smart_search`, `patch_file`, web search, notifications, Gemini and OpenAI. |
| Apr–May 2026 | Voice (VibeVoice), XML agent protocol with auto-repair. ~210 commits. |
| Oct–Nov 2026 | Brain Server, web UI (jarvis-web), pairing and TOTP, relay mode, knowledge and long-term memory. 3.x releases. |

### Original README review (done)

- R1–R10: factual errors (version 3.3.0 vs 3.8.1, Python badge, two broken links, `python main.py`,
  undocumented flags, "openapi", vague `--modules`, non-existent example tasks, `./run.sh` vs `ai`).
- T1–T7: "AAA" tone (framework, banner as spec, "auto-detects hardware", jargon headings and flag
  descriptions, inflated feature names, no status section).
- Follow-ups still open: P1 (`requires-python`), P2 (badge bumped by hand) — in FINDINGS.
