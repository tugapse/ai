import subprocess
import os
import sys
import argparse
from pathlib import Path

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def get_confirmation(prompt, auto_accept):
    """Handles user input or auto-accept logic."""
    if auto_accept:
        return True
    while True:
        res = input(f"{Colors.BLUE}{prompt} (y/n): {Colors.ENDC}").strip().lower()
        if res in ['y', 'yes']: return True
        if res in ['n', 'no']: return False
        print(f"{Colors.WARNING}Please enter 'y' or 'n'.{Colors.ENDC}")

def ensure_venv(auto_accept):
    """
    Ensures a virtual environment exists. 
    If not in one, it creates/activates it and restarts the script.
    """
    venv_dir = Path(".venv")
    
    # Check if we are already in the venv
    if sys.prefix == str(venv_dir.absolute()):
        return

    print(f"\n{Colors.HEADER}--- Step 0: Environment Provisioning ---{Colors.ENDC}")
    
    if not venv_dir.exists():
        if get_confirmation("Virtual environment (.venv) not found. Create it?", auto_accept):
            print(f"{Colors.CYAN}Creating virtual environment...{Colors.ENDC}")
            subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
        else:
            print(f"{Colors.WARNING}Continuing with current environment: {sys.prefix}{Colors.ENDC}")
            return

    # Path to the venv's python
    python_exe = venv_dir / ("Scripts" if os.name == 'nt' else "bin") / ("python.exe" if os.name == 'nt' else "python")

    print(f"{Colors.GREEN}Switching context to venv: {python_exe}{Colors.ENDC}")
    # This replaces the current process with the one inside the venv
    os.execv(str(python_exe), [str(python_exe)] + sys.argv)

def install_standard_reqs(auto_accept):
    """Installs requirements.txt using the active environment's pip."""
    req_path = Path("requirements.txt")
    if not req_path.exists():
        return

    print(f"\n{Colors.HEADER}--- Step 1: Standard Dependencies ---{Colors.ENDC}")
    if get_confirmation("Install requirements.txt?", auto_accept):
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(req_path)], check=True)

def install_llama_cpp(auto_accept):
    """Builds llama-cpp-python with CUDA support if a GPU is found."""
    print(f"\n{Colors.HEADER}--- Step 2: Llama-CPP Build ---{Colors.ENDC}")
    
    # Simple check for nvidia-smi
    has_gpu = subprocess.run(['nvidia-smi'], capture_output=True).returncode == 0
    
    if has_gpu and get_confirmation("NVIDIA GPU found. Build llama-cpp with CUDA?", auto_accept):
        env_vars = os.environ.copy()
        env_vars.update({
            "CMAKE_ARGS": "-DGGML_CUDA=on -DCMAKE_CUDA_ARCHITECTURES=native",
            "FORCE_CMAKE": "1"
        })
        subprocess.run([
            sys.executable, "-m", "pip", "install", "llama-cpp-python", 
            "--no-cache-dir", "--force-reinstall"
        ], env=env_vars, check=True)

def fire_engine_installer():
    """Triggers the engine script using the EXACT same environment."""
    engine_script = Path("scripts/install_engines.py")
    
    print(f"\n{Colors.HEADER}--- Step 3: Engine Logic Injection ---{Colors.ENDC}")
    
    if not engine_script.exists():
        print(f"{Colors.FAIL}Error: {engine_script} not found.{Colors.ENDC}")
        return

    print(f"{Colors.CYAN}Executing {engine_script} within current env...{Colors.ENDC}")
    # Using sys.executable ensures the engine script uses the venv we just set up
    subprocess.run([sys.executable, str(engine_script)], check=True)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--auto-accept", "-y", action="store_true")
    args = parser.parse_args()

    # 1. Provision/Activate Env
    ensure_venv(args.auto_accept)
    
    # 2. Setup Base Deps
    install_standard_reqs(args.auto_accept)
    
    # 3. Setup Heavy AI Deps (Llama)
    install_llama_cpp(args.auto_accept)
    
    # 4. Fire the secondary AI engine script
    fire_engine_installer()

    print(f"\n{Colors.GREEN}{Colors.BOLD}All systems provisioned.{Colors.ENDC}")

if __name__ == "__main__":
    main()