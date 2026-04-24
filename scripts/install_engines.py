import os
import sys
import subprocess
import json
import shutil

C_BOLD = "\033[1m"
C_GREEN = "\033[92m"
C_RED = "\033[91m"
C_YELLOW = "\033[93m"
C_BLUE = "\033[94m"
C_CYAN = "\033[96m"
C_END = "\033[0m"

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONFIG_FILE = os.path.join(BASE_DIR, "installed_engines.json")
VENV_DIR = os.path.join(BASE_DIR, ".venv")

SYSTEM_REQS = {
    "gguf": {
        "binary": "gcc",
        "generic": "GCC, G++, CMake, Make",
        "debian": "build-essential cmake",
        "arch": "base-devel cmake"
    },
    "voice_engine": {
        "binary": "portaudio",
        "generic": "PortAudio, libsndfile",
        "debian": "portaudio19-dev libsndfile1",
        "arch": "portaudio libsndfile"
    },
    "vector_memory": {
        "binary": "sqlite3",
        "generic": "SQLite3 Development Headers",
        "debian": "sqlite3 libsqlite3-dev",
        "arch": "sqlite"
    },
    "ollama": {
        "binary": "curl",
        "generic": "Curl",
        "debian": "curl",
        "arch": "curl"
    }
}

class SystemDiagnostics:
    @staticmethod
    def get_distro():
        if os.path.exists("/etc/os-release"):
            with open("/etc/os-release") as f:
                content = f.read().lower()
                if "ubuntu" in content or "debian" in content:
                    return "debian"
                if "arch" in content:
                    return "arch"
        return "other"

    @staticmethod
    def check_engine_deps(engine_id):
        req = SYSTEM_REQS.get(engine_id)
        if not req:
            return True

        binary_to_check = req["binary"]
        has_binary = shutil.which(binary_to_check)
        
        # Fallback check for compilers if specific binary isn't found
        if engine_id in ["gguf", "vector_memory"] and not has_binary:
            has_binary = shutil.which("gcc") or shutil.which("g++")

        if not has_binary:
            distro = SystemDiagnostics.get_distro()
            print(f"\n{C_RED}{C_BOLD}[!] SYSTEM DEPENDENCY MISSING: {engine_id.upper()}{C_END}")
            print(f"{C_CYAN}This engine requires system-level packages to compile or run.{C_END}")
            
            if distro == "debian":
                print(f"{C_YELLOW}Please run:{C_END} {C_BOLD}sudo apt update && sudo apt install {req['debian']}{C_END}")
            elif distro == "arch":
                print(f"{C_YELLOW}Please run:{C_END} {C_BOLD}sudo pacman -S {req['arch']}{C_END}")
            else:
                print(f"{C_YELLOW}Requirement Names:{C_END} {C_BOLD}{req['generic']}{C_END}")
                print(f"Please install these using your system's package manager.")
            
            choice = input(f"\n{C_BOLD}Proceed with pip install anyway? (y/n): {C_END}").lower()
            return choice == 'y'
        return True

ENGINES = [
    {"id": "gguf", "name": "Llama-CPP GGUF", "deps": ["llama-cpp-python", "huggingface-hub", "numpy"]},
    {"id": "transformers", "name": "Transformers (HF)", "deps": ["torch", "transformers", "accelerate", "huggingface-hub", "bitsandbytes>=0.46.1"]},
    {"id": "ollama", "name": "Ollama (Local API)", "deps": ["ollama", "requests"]},
    {"id": "openai", "name": "OpenAI (Cloud API)", "deps": ["openai"]},
    {"id": "gemini_api", "name": "Gemini (API Key)", "deps": ["google-generativeai"]},
    {"id": "gemini_vertex", "name": "Gemini (Vertex AI)", "deps": ["google-cloud-aiplatform"]},
    {"id": "server_hub", "name": "Neural Hub (Main PC Server)", "deps": ["fastapi", "uvicorn", "pydantic", "python-multipart"]},
    {"id": "client_link", "name": "Neural Link (Tiny PC Client)", "deps": ["requests", "pydantic"]},
    {"id": "vector_memory", "name": "Long Term Memory (ChromaDB)", "deps": ["sentence-transformers", "chromadb"]},
    {"id": "voice_engine", "name": "Voice Module (Realtime TTS)", "deps": ["huggingface-hub>=0.34.0,<1.0", "vibevoice[streamingtts] @ git+https://github.com/microsoft/VibeVoice.git", "torch", "transformers", "soundfile", "librosa", "einops", "pyaudio"]},
]

def setup_venv():
    if not os.path.exists(VENV_DIR):
        print(f"{C_YELLOW}>>> .venv not found. Creating virtual environment...{C_END}")
        subprocess.run([sys.executable, "-m", "venv", VENV_DIR], check=True)
    
    if os.name == "nt":
        return os.path.join(VENV_DIR, "Scripts", "python.exe")
    return os.path.join(VENV_DIR, "bin", "python")

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except: return {}
    return {}

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def main_menu():
    venv_python = setup_venv()
    
    while True:
        config = load_config()
        clear_screen()
        print(f"{C_CYAN}{C_BOLD}==============================================")
        print("      JARVIS AI ENGINE MANAGER & INSTALLER       ")
        print(f"=============================================={C_END}\n")
        
        for i, eng in enumerate(ENGINES, 1):
            is_installed = config.get(eng['id'], {}).get("installed", False)
            status_text = f"{C_GREEN}[INSTALLED]{C_END}" if is_installed else f"{C_RED}[NOT INSTALLED]{C_END}"
            print(f"{C_BOLD}{i:2}. {eng['name']:<35}{C_END} {status_text}")

        print(f"\n{C_CYAN}----------------------------------------------{C_END}")
        print(f"{C_GREEN}[a] Install/Update Engine{C_END}")
        print(f"{C_RED}[r] Remove Engine{C_END}")
        print(f"{C_BOLD}[q] Quit{C_END}")
        print(f"{C_CYAN}----------------------------------------------{C_END}")
        
        choice = input(f"\n{C_BOLD}Action:{C_END} ").lower().strip()
        
        if choice == 'q': break
        elif choice == 'a': install_flow(config, venv_python)
        elif choice == 'r': uninstall_flow(config, venv_python)

def install_flow(config, venv_python):
    clear_screen()
    print(f"{C_YELLOW}{C_BOLD}--- Select engine to INSTALL ---{C_END}\n")
    for i, eng in enumerate(ENGINES, 1):
        print(f"{i}. {eng['name']}")
    
    idx_input = input(f"\n{C_BOLD}Number (or 'b' to go back):{C_END} ")
    if idx_input.isdigit():
        idx = int(idx_input) - 1
        if 0 <= idx < len(ENGINES):
            run_pip(ENGINES[idx], config, venv_python, "install")

def uninstall_flow(config, venv_python):
    clear_screen()
    print(f"{C_RED}{C_BOLD}--- Select engine to REMOVE ---{C_END}\n")
    installed = [e for e in ENGINES if config.get(e['id'], {}).get("installed")]
    if not installed:
        input(f"{C_RED}No engines installed. Press Enter...{C_END}")
        return
    for i, eng in enumerate(installed, 1):
        print(f"{i}. {eng['name']}")
    
    idx_input = input(f"\n{C_BOLD}Number to UNINSTALL (or 'b' to go back):{C_END} ")
    if idx_input.isdigit():
        idx = int(idx_input) - 1
        if 0 <= idx < len(installed):
            run_pip(installed[idx], config, venv_python, "uninstall")

def run_pip(engine, config, venv_python, action):
    env = os.environ.copy()
    deps = engine['deps']
    
    cmd = [venv_python, "-m", "pip", action]
    
    if action == "install":
        if not SystemDiagnostics.check_engine_deps(engine['id']):
            print(f"{C_RED}>>> Installation aborted.{C_END}")
            input("\nPress Enter to return to menu...")
            return

        if engine['id'] == "gguf":
            gpu = input(f"{C_CYAN}Enable CUDA (GPU) support for GGUF? (y/n): {C_END}").lower() == 'y'
            if gpu:
                print(f"\n{C_YELLOW}--- Select CUDA Version ---{C_END}")
                print(f"{C_BOLD}1.{C_END} Modern NVIDIA (CUDA 12.x - Recommended)")
                print(f"{C_BOLD}2.{C_END} Older NVIDIA (CUDA 11.x)")
                print(f"{C_BOLD}3.{C_END} Build from Source (Advanced/Custom Hardware)")
                
                cuda_choice = input(f"\n{C_CYAN}Select option (1/2/3): {C_END}").strip()

                if cuda_choice == '1':
                    cmd += [
                        "--extra-index-url", "https://abetlen.github.io/llama-cpp-python/whl/cu124",
                        "--no-cache-dir", "--force-reinstall", "--upgrade"
                    ]
                elif cuda_choice == '2':
                    cmd += [
                        "--extra-index-url", "https://abetlen.github.io/llama-cpp-python/whl/cu114",
                        "--no-cache-dir", "--force-reinstall", "--upgrade"
                    ]
                else:
                    # Source build requires local compilation directives
                    arch = input(f"{C_CYAN}Enter GPU architecture (e.g., 86 for RTX 3000) or press Enter for 'native': {C_END}").strip()
                    arch = arch if arch else "native"
                    env["CMAKE_ARGS"] = f"-DGGML_CUDA=on -DCMAKE_CUDA_ARCHITECTURES={arch}"
                    env["FORCE_CMAKE"] = "1"
                    cmd += ["--no-cache-dir", "--force-reinstall", "--upgrade"]
            else:
                cmd += ["--upgrade"]
        else:
            cmd += ["--upgrade"]
            
        cmd += deps

        if engine['id'] == "server_hub":
            print(f"{C_YELLOW}>>> Installing Brain Server (FastAPI). Ensure a LLM ENGINE is also installed.{C_END}")
        
        if engine['id'] == "client_link":
            print(f"{C_CYAN}>>> Installing Neural Link (Requests). Connect via --remote [URL].{C_END}")

        if engine['id'] == "voice_engine":
            print(f"{C_YELLOW}>>> Note: VibeVoice-Realtime requires CUDA for optimal performance.{C_END}")

    else:
        # Prevent uninstallation of shared dependencies across engines
        current_config = load_config()
        other_deps = set()
        for e in ENGINES:
            if e['id'] != engine['id'] and current_config.get(e['id'], {}).get("installed"):
                other_deps.update(e['deps'])
        
        to_remove = [d for d in deps if d not in other_deps]
        if not to_remove:
            config[engine['id']] = {"installed": False}
            save_config(config)
            print(f"{C_YELLOW}>>> Dependencies shared. Registry updated without uninstallation.{C_END}")
            return
        cmd = [venv_python, "-m", "pip", "uninstall", "-y"] + to_remove

    try:
        print(f"\n{C_BLUE}>>> Executing {action} for {engine['name']}...{C_END}")
        subprocess.run(cmd, env=env, check=True)
        config[engine['id']] = {"installed": (action == "install")}
        save_config(config)
        print(f"\n{C_GREEN}>>> Success!{C_END}")
    except Exception as e:
        print(f"\n{C_RED}>>> Error: {e}{C_END}")
    input("\nPress Enter to continue...")

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print(f"\n{C_YELLOW}Exiting Engine Manager...{C_END}")
    finally:
        sys.exit(0)