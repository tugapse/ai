# 9. Installation

- [Requirements](#requirements)
- [Linux](#linux)
- [Optional engines](#optional-engines)
- [GPU builds](#gpu-builds)
- [Windows](#windows)
- [Installing as a package](#installing-as-a-package)
- [Updating](#updating)
- [Troubleshooting](#troubleshooting)

---

## Requirements

- **Python 3.10–3.13**, with `venv`. It is developed and tested on 3.13; 3.10 is the minimum the code needs (`X | None` annotations, `str.removeprefix`).
- **Linux** is the main platform. Windows has build scripts and an executable, but gets less testing.
- Optional, depending on what you use:
  - an NVIDIA GPU with CUDA for fast local models (GGUF/Transformers) and the voice;
  - a C/C++ toolchain and CMake to build `llama-cpp-python`;
  - Node.js (`npx`) for the shipped MCP servers;
  - PortAudio + libsndfile for the voice;
  - Ollama, or API keys for OpenAI / Gemini, if you use those.

## Linux

```bash
git clone https://github.com/tugapse/ai.git
cd ai
./build.sh
```

What `build.sh` does:
1. creates `.venv` if it doesn't exist;
2. upgrades pip and installs `requirements.txt` (the base: `prompt_toolkit`, `requests`, `mcp`,
   `numpy`, `colorama`, …) via `scripts/dependency_installer.py`;
3. opens the **engine menu** (`scripts/install_engines.py`) so you pick what else to install.

Then:

```bash
./run.sh --version
./run.sh                       # first run creates ~/Ai (your AI folder)
```

`run.sh` activates `.venv`, sets `PYTHONPATH=src` and runs `src/ai/main.py` with your arguments.

## Optional engines

Everything heavy is optional. Open the menu any time with:

```bash
./run.sh install
```

Choosing an installed engine offers to uninstall it (shared dependencies are kept).
What's installed is recorded in `installed_engines.json` in the project folder, and JARVIS checks it
before loading a model or module.

| Engine | For | Main packages | System packages (Debian / Arch) |
|--------|-----|---------------|---------------------------------|
| Llama-CPP GGUF | `gguf` models | `llama-cpp-python`, `huggingface-hub` | `build-essential cmake` / `base-devel cmake` |
| Transformers (HF) | `causal_lm` models | `torch`, `transformers`, `accelerate`, `bitsandbytes`, … | — |
| Ollama (Local API) | `ollama` models | `ollama` | `curl` (and Ollama itself) |
| OpenAI (Cloud API) | `openai` models | `openai` | — |
| Gemini (API Key & Vertex AI) | `gemini` models | `google-genai`, `pillow` | — |
| Neural Hub (Main PC Server) | `ai server` | `fastapi`, `uvicorn`, `pydantic`, `python-multipart` | — |
| Neural Link (Tiny PC Client) | `jarvis` models (talk to a server) | `requests`, `pydantic` | — |
| Long Term Memory (ChromaDB) | Long-term memory, semantic knowledge search | `sentence-transformers`, `chromadb` | `sqlite3 libsqlite3-dev` / `sqlite` |
| Voice Module (Realtime TTS) | Voice | VibeVoice (from GitHub), `torch`, `soundfile`, `librosa`, `pyaudio` | `portaudio19-dev libsndfile1` / `portaudio libsndfile` |

The menu checks the system packages and prints the command for your distro when one is missing.

## GPU builds

**GGUF with CUDA.** When installing the GGUF engine, the menu asks whether to enable CUDA, reads
your CUDA version from `nvidia-smi` and lets you confirm it (13.x, 12.x, 11.4…), then builds
`llama-cpp-python` for it.

To build by hand (inside `.venv`):

```bash
# NVIDIA / CUDA (Linux or Windows)
CMAKE_ARGS="-DGGML_CUDA=on -DGGML_CUDA_FORCE_CUBLAS=on -DLLAVA_BUILD=off -DCMAKE_CUDA_ARCHITECTURES=native" FORCE_CMAKE=1 \
  pip install llama-cpp-python --no-cache-dir --force-reinstall --upgrade
```

```powershell
# AMD on Windows with Vulkan (needs the Vulkan SDK; VULKAN_SDK and VULKAN_SDK_PATH set)
$env:CMAKE_ARGS = "-DGGML_VULKAN=on"
pip install llama-cpp-python --no-cache-dir --force-reinstall --upgrade
```

```bash
# PyTorch on AMD with DirectML (Windows)
pip install torch-directml
```

If a model doesn't fit in the GPU when loading, JARVIS offers alternatives instead of crashing
(see [Models](06-models.md#when-the-model-doesnt-fit-in-the-gpu)).

## Windows

```powershell
.\build.ps1           # same as build.sh: .venv, requirements, engine menu
.\run.ps1             # run from the checkout (run.cmd also works)
```

**Executable.** `compile.ps1` builds `dist\ai.exe`, which bundles `run.ps1`, the Python source, the
assets and the installer:

```powershell
.\compile.ps1
```

- `ai.exe` needs a `.venv` folder next to it: copy both together to run without the source checkout
  (e.g. `.\ai.exe -m "hello"`).
- `compile.ps1` uses the environment in `AI_VENV_PATH` if set (relative paths are resolved from the
  project folder); otherwise `.venv` in the project folder or its parent; otherwise `python` on
  `PATH`.
- `.\ai.exe install` adds engines; it updates `installed_engines.json` beside the EXE.

> On Windows `smart_search` searches file contents in Python when there's no `grep` on `PATH`, and
> desktop notifications fall back to the terminal bell when no notifier is available.

## Installing as a package

Each GitHub release is published to a package index on GitHub Pages
(`https://tugapse.github.io/python-index/`):

```bash
pip install --extra-index-url https://tugapse.github.io/python-index/ ai
ai --version
```

This installs the `ai` command (same as `./run.sh`). The engines are still installed with
`ai install`.

## Updating

```bash
git pull
./build.sh            # picks up new base requirements
```

Your AI folder isn't touched by an update. New versions of shipped templates (pipelines, prompts,
model configs in `system/`) are **not** copied over your existing ones; to get them, delete the
files you want refreshed from `~/Ai/system/` and run JARVIS again (see
[Configuration](08-configuration.md#how-templates-are-copied)).

## Troubleshooting

| Problem | Try |
|---------|-----|
| "The engine for X is not installed" | `./run.sh install` and pick that engine. |
| `llama-cpp-python` fails to build | Install the toolchain (`build-essential cmake` / `base-devel cmake`); for CUDA make sure `nvcc` matches the version you picked. |
| GGUF runs on the CPU only | It was built without CUDA: reinstall the GGUF engine with CUDA, or build by hand (above). Check `n_gpu_layers` is `-1`. |
| Out of GPU memory | Pick one of the alternatives JARVIS offers, lower `n_ctx`, use a smaller quantization, or use the running server. |
| `pyaudio` fails to install | Install PortAudio first (`portaudio19-dev` / `portaudio`). |
| JARVIS waits on stdin | Something left stdin open: pass the prompt with `-m`, or set `AI_STDIN_WAIT=0`. |
| MCP servers fail to start | They need Node.js (`npx`); GitHub also needs a token in `env`. `ai mcp disable NAME` turns one off. |
| Settings "reset" / templates missing | Check `AI_ASSISTANT_DIRECTORY` (default `~/Ai`). Don't use `ai config reset` unless you mean it: it resets `config.json`. |
| Something else | Run with `-pl` (logs) or `-pdb` (debug), or `-dc` to keep the screen from clearing. |
