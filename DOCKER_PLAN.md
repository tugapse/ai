# Comprehensive Dockerization Plan for JARVIS AI Assistant

## 1. Overview & Objectives
Transform the project into a fully containerized ecosystem capable of running:
- **Interactive Agent / CLI Mode**: Command-line interactive agent (`ai`).
- **Neural Hub Server Mode**: Headless FastAPI backend running on port `8000`.
- **Automated Test Suite Runner**: Isolated environment for running unit (`pytest`) and integration tests (`run-tests.sh`).
- **Extensible GPU Support**: Support both standard CPU and CUDA-accelerated builds (for `llama-cpp-python` and PyTorch/Transformers).

---

## 2. Architecture & File Blueprint

### A. Environment Configuration (`.dockerignore`) [COMPLETED]
Exclude non-essential host assets to minimize build context size and prevent venv/cache pollution:
- `.venv`, `__pycache__`, `*.pyc`, `*.pyo`
- `.git`, `.pytest_cache`, `.coverage`
- Local logs (`logs/*`) and temporary files (`temp_*`)
- Host binary builds or compiled C extension artifacts

### B. Core Container Image (`Dockerfile`) [COMPLETED]
- **Base Image**: `python:3.11-slim` (Debian-based for binary package compatibility).
- **System Dependencies Installed**:
  - `build-essential`, `cmake`, `gcc`, `g++` (required for C/C++ engine compilations like `llama-cpp` or SQLite extensions).
  - `portaudio19-dev`, `libsndfile1`, `ffmpeg` (required for real-time voice & audio TTS/STT engines).
  - `sqlite3`, `libsqlite3-dev` (required for ChromaDB vector memory).
  - `curl`, `git` (required for fetching external repository submodules/weights).
- **Python Environment**:
  - Upgrade `pip`, `setuptools`, and `wheel`.
  - Install dependencies from `requirements.txt` and `pyproject.toml`.
- **Environment Variables**:
  - `PYTHONUNBUFFERED=1`
  - `PYTHONPATH=/app/src`
  - `AI_ASSISTANT_DIRECTORY=/app`
  - `TQDM_DISABLE=1`
- **Exposed Ports**: `8000` (FastAPI Brain Server)

### C. Smart Container Entrypoint (`docker-entrypoint.sh`) [COMPLETED]
Supports parameter routing:
- Default execution (no flags or custom flags): `python3 /app/src/ai/main.py "$@"`
- Server command (`--server`): launches `uvicorn ai.modules.server.server_module:app --host 0.0.0.0 --port 8000`
- Test command (`test` / `--test`): executes `./run-tests.sh -a` or `pytest tests/`

### D. Multi-Container Orchestration (`docker-compose.yml`) [COMPLETED]
1. **`ai-server`**: Runs the FastAPI Neural Hub in server mode on port 8000 with volume mounts for persistent memory and logs.
2. **`ai-cli`**: Ephemeral interactive agent container connected to `ai-server`.
3. **`ollama`** (Optional profile): Local Ollama container serving GGUF models on port 11434 with shared Docker bridge network.

---

## 3. Implementation Status

### Milestone 1: Dockerfile & Base Setup [COMPLETED]
- [x] Create `.dockerignore` to filter out `.venv`, caches, and build artifacts.
- [x] Create standard `Dockerfile`.
- [x] Create `docker-entrypoint.sh` with execution routing for CLI, Server, and Testing.

### Milestone 2: Service Orchestration [COMPLETED]
- [x] Create `docker-compose.yml` exposing ports and setting up persistent volume mounts (`./logs`, `./storage`, `./sessions`, `./system`, `./installed_engines.json`).
- [x] Implement healthcheck endpoints for container readiness monitoring (`GET /api/health`).

### Milestone 3: Testing & Verification [COMPLETED]
- [x] Validate syntax and compose specification via `docker compose config`.
- [x] Ensure permissions on `docker-entrypoint.sh`.

---

## 4. Usage Commands Quick Reference

```bash
# Build Docker Image
docker build -t ai-assistant:latest .

# Run Interactive CLI Mode
docker run -it --rm ai-assistant:latest

# Run Server Mode
docker run -d -p 8000:8000 --name ai-server ai-assistant:latest --server

# Run Complete Test Suite inside Docker
docker run --rm ai-assistant:latest test

# Launch via Docker Compose
docker compose up -d ai-server

# Launch interactive CLI container via Compose
docker compose run --rm ai-cli

# Launch with Ollama sidecar
docker compose --profile with-ollama up -d
```