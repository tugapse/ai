import subprocess
import os
import sys
import argparse
from pathlib import Path
import importlib.util

class Colors:
    HEADER = '\033[95;1m'
    BLUE   = '\033[94m'
    CYAN   = '\033[96m'
    GREEN  = '\033[92m'
    YLW    = '\033[93m'
    RED    = '\033[91m'
    END    = '\033[0m'
    BOLD   = '\033[1m'

def is_installed(module_name):
    """Checks if a module exists without importing it (prevents side effects)."""
    return importlib.util.find_spec(module_name) is not None

def get_confirmation(prompt, auto_accept):
    if auto_accept: return True
    res = input(f"{Colors.BLUE}{prompt} (y/n): {Colors.END}").strip().lower()
    return res in ['y', 'yes', '']

def ensure_venv(auto_accept):
    venv_dir = Path(".venv")
    # Check if currently running from the venv
    if sys.prefix == str(venv_dir.absolute()):
        return

    print(f"\n{Colors.HEADER}[ 0 ] ENVIRONMENT PROVISIONING{Colors.END}")
    
    if not venv_dir.exists():
        if get_confirmation("Virtual environment (.venv) not found. Create it?", auto_accept):
            print(f"{Colors.CYAN}Creating virtual environment...{Colors.END}")
            subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)
        else:
            print(f"{Colors.YLW}Warning: Proceeding without virtual environment.{Colors.END}")
            return

    # Determine executable path
    bin_name = "Scripts" if os.name == 'nt' else "bin"
    exe_name = "python.exe" if os.name == 'nt' else "python"
    python_exe = venv_dir / bin_name / exe_name

    print(f"{Colors.GREEN}Context Shift: Re-launching within .venv...{Colors.END}")
    os.execv(str(python_exe), [str(python_exe)] + sys.argv)

def install_standard_reqs(auto_accept):
    req_path = Path("requirements.txt")
    if not req_path.exists(): return

    print(f"\n{Colors.HEADER}[ 1 ] CORE DEPENDENCIES{Colors.END}")
    
    # Always upgrade pip first for build stability
    subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], 
                   stdout=subprocess.DEVNULL)

    if get_confirmation("Sync requirements.txt?", auto_accept):
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(req_path)], check=True)

def install_llama_cpp(auto_accept):
    print(f"\n{Colors.HEADER}[ 2 ] ACCELERATED COMPUTING (LLAMA-CPP){Colors.END}")
    
    if is_installed("llama_cpp"):
        print(f"{Colors.GREEN}Llama-CPP is already installed and mapped.{Colors.END}")
        return

    # Silent GPU Check
    has_gpu = False
    try:
        # We capture output to keep the terminal clean
        subprocess.run(['nvidia-smi'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        has_gpu = True
    except:
        has_gpu = False
    
    if has_gpu:
        print(f"{Colors.CYAN}NVIDIA GPU detected via hardware bus.{Colors.END}")
        if get_confirmation("Build llama-cpp with CUDA support?", auto_accept):
            env_vars = os.environ.copy()
            env_vars.update({
                "CMAKE_ARGS": "-DGGML_CUDA=on -DCMAKE_CUDA_ARCHITECTURES=native",
                "FORCE_CMAKE": "1"
            })
            print(f"{Colors.YLW}Compiling... this may take several minutes.{Colors.END}")
            subprocess.run([
                sys.executable, "-m", "pip", "install", "llama-cpp-python", "--no-cache-dir"
            ], env=env_vars, check=True)
    else:
        print(f"{Colors.YLW}No GPU detected or CUDA drivers missing. Installing CPU version.{Colors.END}")
        subprocess.run([sys.executable, "-m", "pip", "install", "llama-cpp-python"], check=True)

def fire_engine_installer():
    engine_script = Path("scripts/install_engines.py")
    print(f"\n{Colors.HEADER}[ 3 ] ENGINE LOGIC INJECTION{Colors.END}")
    
    if not engine_script.exists():
        print(f"{Colors.RED}Skipping: {engine_script} not found.{Colors.END}")
        return

    print(f"{Colors.CYAN}Executing {engine_script.name}...{Colors.END}")
    subprocess.run([sys.executable, str(engine_script)], check=True)

def main():
    parser = argparse.ArgumentParser(description="JARVIS Dependency Provisioner")
    parser.add_argument("--auto-accept", "-y", action="store_true")
    args = parser.parse_args()

    try:
        ensure_venv(args.auto_accept)
        install_standard_reqs(args.auto_accept)
        # install_llama_cpp(args.auto_accept)
        fire_engine_installer()
        print(f"\n{Colors.GREEN}{Colors.BOLD}>>> SYSTEM READY: ALL ENGINES PROVISIONED <<<{Colors.END}\n")
    except Exception as e:
        print(f"\n{Colors.RED}[!] Provisioning Failed: {e}{Colors.END}")
        sys.exit(1)

if __name__ == "__main__":
    main()