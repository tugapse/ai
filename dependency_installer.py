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
        print(f"{Colors.CYAN}{prompt} (Auto-accepted).{Colors.ENDC}")
        return True
    
    while True:
        res = input(f"{Colors.BLUE}{prompt} (y/n): {Colors.ENDC}").strip().lower()
        if res in ['y', 'yes']: return True
        if res in ['n', 'no']: return False
        print(f"{Colors.WARNING}Please enter 'y' or 'n'.{Colors.ENDC}")

def has_nvidia_gpu():
    """Checks if an NVIDIA GPU is accessible via nvidia-smi."""
    try:
        subprocess.run(['nvidia-smi'], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def install_standard_reqs(auto_accept):
    """Installs dependencies from requirements.txt."""
    req_path = Path(__file__).parent / "requirements.txt"
    
    print(f"\n{Colors.HEADER}--- Step 1: Standard Dependencies ---{Colors.ENDC}")
    
    if not req_path.exists():
        print(f"{Colors.WARNING}requirements.txt not found at {req_path}. Skipping.{Colors.ENDC}")
        return

    if get_confirmation("Install dependencies from requirements.txt?", auto_accept):
        print(f"{Colors.CYAN}Installing...{Colors.ENDC}")
        try:
            # We skip the pip upgrade here to avoid permission issues in some envs
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(req_path)], check=True)
            print(f"{Colors.GREEN}Standard dependencies installed successfully.{Colors.ENDC}")
        except subprocess.CalledProcessError as e:
            print(f"{Colors.FAIL}Installation failed: {e}{Colors.ENDC}")

def install_llama_cpp(auto_accept):
    """Installs llama-cpp-python with optimized CMAKE args."""
    print(f"\n{Colors.HEADER}--- Step 2: Llama-CPP Optimization ---{Colors.ENDC}")
    
    gpu_detected = has_nvidia_gpu()
    if not gpu_detected:
        print(f"{Colors.WARNING}No NVIDIA GPU detected. Skipping CUDA-specific build.{Colors.ENDC}")
        return

    print(f"{Colors.CYAN}NVIDIA GPU detected. Preparing CUDA-enabled build...{Colors.ENDC}")
    
    if get_confirmation("Install llama-cpp-python with CUDA support?", auto_accept):
        # Merge existing env with our CUDA flags
        custom_env = os.environ.copy()
        custom_env.update({
            "CMAKE_ARGS": "-DGGML_CUDA=on -DGGML_CUDA_FORCE_CUBLAS=on -DLLAVA_BUILD=off -DCMAKE_CUDA_ARCHITECTURES=native",
            "FORCE_CMAKE": "1"
        })

        cmd = [
            sys.executable, "-m", "pip", "install", "llama-cpp-python",
            "--no-cache-dir", "--upgrade", "--force-reinstall"
        ]

        try:
            print(f"{Colors.CYAN}Running build (this may take a few minutes)...{Colors.ENDC}")
            subprocess.run(cmd, env=custom_env, check=True)
            print(f"{Colors.GREEN}llama-cpp-python with CUDA installed successfully.{Colors.ENDC}")
        except subprocess.CalledProcessError as e:
            print(f"{Colors.FAIL}Build failed. Ensure CUDA Toolkit is installed and in your PATH.{Colors.ENDC}")

def main():
    parser = argparse.ArgumentParser(description="Python Dependency Installer V2")
    parser.add_argument("--auto-accept", "-y", action="store_true", help="Skip prompts")
    args = parser.parse_args()

    print(f"{Colors.HEADER}{Colors.BOLD}Python Dependency Installer V2{Colors.ENDC}")
    
    install_standard_reqs(args.auto_accept)
    install_llama_cpp(args.auto_accept)

    print(f"\n{Colors.GREEN}{Colors.BOLD}Process Complete.{Colors.ENDC}")

if __name__ == "__main__":
    main()