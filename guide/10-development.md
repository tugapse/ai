# 10. Development

How the code is organised, how to test it, and how releases are made.

- [Code map](#code-map)
- [Running from source](#running-from-source)
- [Tests](#tests)
- [Conventions](#conventions)
- [Releases](#releases)
- [Generated docs and knowledge](#generated-docs-and-knowledge)
- [Utilities](#utilities)
- [Documentation](#documentation)

---

## Code map

```
src/ai/
├── main.py, cli_args.py     entry point, mode dispatch                   → 2. Program
├── cli/                     command line: one file per command group     → 10 (Adding a CLI command)
├── program.py, config.py    Program, ProgramConfig / ProgramSetting      → 2, 8
├── direct.py, stdin_reader.py   one-shot answers, safe stdin              → 1. Interfaces
├── chat/                    plain chat prompt                            → 1
├── agents/                  agent loop, parser, context, sessions        → 3. Agents
│   └── chat_ui/             interactive agent chat                       → 1
├── tools/                   @tool, categories, registry, MCP bridge      → 4. Tools
├── modules/
│   ├── tools_*/             built-in tool categories                     → 4
│   ├── knowledge/           project knowledge                            → 5. Knowledge & memory
│   ├── vector_memory/       long-term memory                             → 5
│   ├── server/              Brain Server (FastAPI) + bundled web UI      → 7. Server
│   └── voice/               VibeVoice                                    → 1
├── core/
│   ├── llms/                model providers                              → 6. Models
│   └── events.py, template_injection.py, context_file.py
├── services/                model/stream/UI orchestration, registry...   → 2
├── extras/                  console output, thinking parser
└── entities/                enums

assets/
├── templates/system/        defaults copied to ~/Ai/system               → 8. Configuration
├── templates/user/          defaults copied to ~/Ai/user                 → 8
└── voices/                  VibeVoice voice files
scripts/                     installers, server watchdog, utilities       → 9. Installation
tests/                       pytest suite, CLI integration tests
```

## Adding a CLI command

The command line lives in `src/ai/cli/`, one file per command group:

| File | Commands |
|------|----------|
| `base.py` | Shared options (`-m`, `-md`, `-f`, `-t`, `-o`, debug flags), the help formatter, `DEFAULTS` |
| `agent.py` | `ai agent` |
| `sessions.py` | `ai sessions list` |
| `knowledge.py` | `ai knowledge build / list / forget` |
| `models.py` | `ai models list / generate` |
| `tools.py` | `ai tools create` |
| `mcp.py` | `ai mcp list / enable / disable` |
| `server.py` | `ai server`, `ai server totp-setup`, `ai server frontend` |
| `setup.py` | `ai install`, `ai config reset` |
| `__init__.py` | Builds the parser, fills defaults, prints the notice for old flags, runs the handlers |

Each group module defines:

- `register(subparsers, parent)` — its sub-command(s), options and help text;
- `DEFAULTS` — the `args` attributes it sets, with their defaults;
- `LEGACY` + `add_legacy(parser)` — old top-level flags it replaces (still accepted, hidden);
- `MAINTENANCE` — handlers `fn(prog, args, directory_manager)` that run **before** the model loads;
  each returns when its option isn't set and exits when it handled the run. `AFTER_MODEL` is the
  same for handlers that need the model (`knowledge build`).

To add a group, write `src/ai/cli/<name>.py` with those names and add it to `COMMAND_MODULES` in
`src/ai/cli/__init__.py`. If its handlers run before the model loads, also add its main `args`
attribute to `maintenance_keys` in `main.py` (so JARVIS doesn't load a model first).

Sub-commands and old flags fill the **same** `args` attributes, so `src/ai/cli_args.py` — which still
dispatches the agent run, server mode and one-shot answers — doesn't care which form was typed.
`tests/ai/test_cli.py` checks that every new form matches its old flag.

## Running from source

```bash
./run.sh ...                        # always runs the code in this checkout
```

When testing changes, use `./run.sh`, not an installed `ai` command, which may be an older version.

To try changes to templates without touching your real setup, use a fresh AI folder:

```bash
AI_ASSISTANT_DIRECTORY=$(mktemp -d) ./run.sh agent
```

## Tests

```bash
./run-tests.sh            # unit tests (default)
./run-tests.sh -u         # unit tests only
./run-tests.sh -c [1-5]   # CLI integration tests (all, or one category); no model, no GPU
./run-tests.sh -a         # everything; -v shows every command and its output
```

The CLI integration tests check the CLI's parameters, not a model. A stub Brain Server
(`tests/e2e/stub_server.py`) stands in for the model through a `jarvis` config: it records each
request and always answers `STUB_OK`, so a test asserts what the CLI sent (system prompt, files,
task, images) and what it did with the answer (`-o`, `-q`, exit codes). Each run uses its own
`AI_ASSISTANT_DIRECTORY` and free ports, so it never touches `~/Ai` or a running Brain Server.
Categories: 1 informational flags and listings, 2 parameters sent to the model, 3 errors and exit
codes, 4 server and relay, 5 agent mode (the stub answers with scripted agent turns from
`STATE/replies/`, so a test drives tool call, tool result and final answer). Known bugs are `known_issue` tests: skipped until fixed
(`STRICT_KNOWN_ISSUES=1` makes them fail).

Or directly: `.venv/bin/python -m pytest -q` (config in `pyproject.toml`: `pythonpath = ["src",
"tests"]`).

- `tests/ai/...` mirrors `src/ai/...`.
- `tests/conftest.py` points `AI_ASSISTANT_DIRECTORY` at a temporary folder for every test run, so
  tests **never read or write your real `~/Ai`**. Keep it that way in new tests.
- CLI integration tests are shell scripts in `tests/e2e/` (categories: info, single turn,
  file-system changes, config/state, blocking), plus Windows variants.
- Some MCP tests start real servers (Playwright); they're skipped when unavailable.

There's no CI for tests yet; run them before a release.

## Conventions

- **Commits**: [Conventional Commits](https://www.conventionalcommits.org) — `feat(scope): ...`,
  `fix(scope): ...`, `chore: ...`, `docs: ...`, `test: ...`. The `commit` task writes one from a
  diff: `git diff --staged | ./run.sh -t commit`.
- **Branches**: git-flow. Work happens on `develop`; `master` holds releases.
- **Docstrings** of `@tool` functions are read by the model: write them for it (see
  [Tools](04-tools.md#writing-your-own-tools)).
- Prefer config over hard-coded values: new settings go in `ProgramSetting` (`config.py`) and in
  the settings reference in [Configuration](08-configuration.md#settings-reference).

## Releases

Releases use git-flow from `develop`:

```bash
git flow release start vX.Y.Z
# one commit: bump pyproject.toml version + new CHANGELOG.md section
#   "chore(release): Bump version to X.Y.Z and update CHANGELOG"
GIT_MERGE_AUTOEDIT=no git flow release finish -m "vX.Y.Z" vX.Y.Z
git push origin master develop --follow-tags
```

- `CHANGELOG.md` gets a `## [vX.Y.Z] - YYYY-MM-DD` section grouped into Features, Bug Fixes and
  Maintenance, listing the commit subjects. The `release/start` and `create-changelog` tasks help.
- `release finish -m` writes the tag message twice ("vX.Y.Z vX.Y.Z"); earlier tags have just
  "vX.Y.Z", so while the tag is still local it's recreated with
  `git tag -f -a vX.Y.Z -m "vX.Y.Z" <master commit>`.
- Publishing a GitHub Release runs `.github/workflows/publish_to_pypi_pages.yml`, which builds the
  package and adds it to the package index (see [Installation](09-installation.md#installing-as-a-package)).
- The README version badge reads `project.version` from `pyproject.toml` on `master`, so it
  updates itself after the release is pushed.

## Generated docs and knowledge

`_docs/` (Markdown per source file) and `_knowledge/` (component JSON) are this repo's own
knowledge, generated by JARVIS itself:

```bash
./run.sh knowledge build src --mode diff:master   # after a feature branch
./run.sh knowledge build src --mode changed       # whatever changed since the last build
```

`docs/` is a small web viewer for that knowledge (`python -m http.server -d docs 8000`, then open
http://localhost:8000; see `docs/README.md`). See
[Knowledge & memory](05-knowledge-memory.md).

## Utilities

| Script | What it does |
|--------|--------------|
| `scripts/bin/clear_pycache.sh` | Removes `__pycache__` folders. |
| `scripts/bin/rs-temp_x` | Shows CPU/GPU temperatures (wrapper around Linux sensors and `nvidia-smi`); handy to watch the GPU during long inference. |
| `scripts/server/jarvis.sh` | Server watchdog (see [Server](07-server.md#keeping-it-running)). |
| `scripts/install_engines.py` | The engine menu (`ai install`). |
| `scripts/dependency_installer.py` | Base requirements (`build.sh`). |

## Documentation

- `README.md` — the front page.
- `guide/` — this guide, one page per layer.
- `CHANGELOG.md` — release notes.

When you change behaviour, update the guide page for that layer (and its settings table).
