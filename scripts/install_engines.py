import os
import sys
import subprocess
import json

# --- ANSI Colors ---
C_BOLD = "\033[1m"
C_GREEN = "\033[92m"
C_RED = "\033[91m"
C_YELLOW = "\033[93m"
C_BLUE = "\033[94m"
C_CYAN = "\033[96m"
C_END = "\033[0m"

# --- Configuration ---
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CONFIG_FILE = os.path.join(BASE_DIR, "installed_engines.json")
VENV_DIR = os.path.join(BASE_DIR, ".venv")

# --- Registry ---
# Added 'vibevoice' for the 0.5B Realtime TTS model
ENGINES = [
    {"id": "gguf", "name": "GGUF (Local Inference)", "deps": ["llama-cpp-python", "huggingface-hub", "numpy"]},
    {"id": "ollama", "name": "Ollama (Local API)", "deps": ["ollama", "requests"]},
    {"id": "transformers", "name": "Transformers (HF)", "deps": ["torch", "transformers", "accelerate", "huggingface-hub"]},
    {"id": "openai", "name": "OpenAI (Cloud API)", "deps": ["openai"]},
    {"id": "gemini_api", "name": "Gemini (API Key)", "deps": ["google-generativeai"]},
    {"id": "gemini_vertex", "name": "Gemini (Vertex AI)", "deps": ["google-cloud-aiplatform"]},
    {"id": "voice_engine", "name": "Voice Module (Realtime TTS)", "deps": ["vibevoice","torch", "transformers", "soundfile", "librosa", "einops", "pyaudio"]},
    {"id": "vector_memory", "name": "Long Term Memory (CromaDB)", "deps": ["sentence-transformers", "chromadb"]},
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
        print("      JARVIS ENGINE MANAGER & INSTALLER       ")
        print(f"=============================================={C_END}\n")
        
        for i, eng in enumerate(ENGINES, 1):
            is_installed = config.get(eng['id'], {}).get("installed", False)
            status_text = f"{C_GREEN}[INSTALLED]{C_END}" if is_installed else f"{C_RED}[NOT INSTALLED]{C_END}"
            
            # UI: NUMBER. NAME [STATUS]
            print(f"{C_BOLD}{i:2}. {eng['name']:<30}{C_END} {status_text}")

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
    
    if action == "install":
        # Handle GGUF specific GPU flags
        if engine['id'] == "gguf":
            gpu = input(f"{C_CYAN}Enable CUDA (GPU) support for GGUF? (y/n): {C_END}").lower() == 'y'
            if gpu:
                env["CMAKE_ARGS"] = "-DGGML_CUDA=on"
                env["FORCE_CMAKE"] = "1"
        
        # Note for VibeVoice requirements
        if engine['id'] == "vibevoice":
            print(f"{C_YELLOW}>>> Note: VibeVoice-Realtime requires CUDA for low-latency output.{C_END}")

        cmd = [venv_python, "-m", "pip", "install", "--upgrade"] + deps
    else:
        # Check for shared deps to avoid breaking other engines
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
        sys.exit(0)