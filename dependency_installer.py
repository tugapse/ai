import subprocess
import os
import sys
import argparse
from pathlib import Path

class Colors:
    HEADER = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    NC = '\033[0m'

class InstallerUI:
    DIVIDER = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    @staticmethod
    def section(title):
        print(f"\n{Colors.BLUE}{InstallerUI.DIVIDER}{Colors.NC}")
        print(f"{Colors.YELLOW}◈ {Colors.BOLD}{title.upper()}{Colors.NC}")
        print(f"{Colors.BLUE}{InstallerUI.DIVIDER}{Colors.NC}")

    @staticmethod
    def info(msg): print(f"{Colors.CYAN}  ℹ {msg}{Colors.NC}")
    @staticmethod
    def success(msg): print(f"{Colors.GREEN}  ✓ {msg}{Colors.NC}")
    @staticmethod
    def warn(msg): print(f"{Colors.YELLOW}  ⚠ {msg}{Colors.NC}")
    @staticmethod
    def error(msg): print(f"{Colors.RED}  ✖ {msg}{Colors.NC}")

def get_confirmation(prompt, auto_accept):
    if auto_accept:
        return True
    res = input(f"{Colors.BLUE}  ❯{Colors.NC} {prompt} (y/n): ").strip().lower()
    return res in ['y', 'yes']

def check_python_version(auto_accept):
    """Checks if Python version is > 3.13 and warns about compatibility."""
    major, minor = sys.version_info[:2]
    if major == 3 and minor > 13:
        InstallerUI.warn(f"Python {major}.{minor} detected.")
        print(f"    {Colors.YELLOW}Versions newer than 3.13 often lack pre-built binaries (wheels).{Colors.NC}")
        print(f"    {Colors.YELLOW}Installation might require a Rust compiler and take much longer.{Colors.NC}")
        
        if not get_confirmation("Do you want to proceed anyway?", auto_accept):
            InstallerUI.error("Installation aborted by user. Please use Python 3.12 or 3.13.")
            sys.exit(1)
        
        # If they continue, we'll set the fix for Pydantic/Rust builds
        os.environ["PYO3_USE_ABI3_FORWARD_COMPATIBILITY"] = "1"
        InstallerUI.info("Compatibility flag enabled (PYO3_USE_ABI3).")

def check_cuda_compiler():
    try:
        subprocess.run(['nvcc', '--version'], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def has_nvidia_gpu():
    try:
        subprocess.run(['nvidia-smi'], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def install_standard_reqs(auto_accept):
    InstallerUI.section("Standard Dependencies")
    req_path = Path(__file__).parent / "requirements.txt"
    
    if not req_path.exists():
        InstallerUI.warn("requirements.txt not found. Skipping.")
        return

    if get_confirmation("Install requirements.txt?", auto_accept):
        InstallerUI.info("Installing via pip...")
        try:
            # We pass current os.environ to keep the PYO3 flag if set
            subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(req_path)], 
                           env=os.environ, check=True)
            InstallerUI.success("Standard dependencies ready.")
        except subprocess.CalledProcessError as e:
            InstallerUI.error(f"Installation failed: {e}")

def install_llama_cpp(auto_accept):
    InstallerUI.section("Llama-CPP Optimization")
    
    gpu = has_nvidia_gpu()
    nvcc = check_cuda_compiler()

    if not gpu:
        InstallerUI.warn("No NVIDIA GPU detected. Using CPU-only build.")
        return

    if not nvcc:
        InstallerUI.error("GPU detected but 'nvcc' not found.")
        InstallerUI.info("Build will likely fail without CUDA Toolkit.")

    if get_confirmation("Compile llama-cpp-python with CUDA support?", auto_accept):
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
            InstallerUI.info("Starting build. This may take a few minutes...")
            subprocess.run(cmd, env=custom_env, check=True)
            InstallerUI.success("llama-cpp-python with CUDA installed.")
        except subprocess.CalledProcessError:
            InstallerUI.error("Build failed. Check CUDA headers.")

def main():
    parser = argparse.ArgumentParser(description="Architect Dependency Installer")
    parser.add_argument("--auto-accept", "-y", action="store_true")
    args = parser.parse_args()

    try:
        print(f"\n{Colors.HEADER}{Colors.BOLD}🚀 Ai Assistant Dependency Installer{Colors.NC}")
        
        # New Check
        check_python_version(args.auto_accept)
        
        # Run installs
        install_standard_reqs(args.auto_accept)
        install_llama_cpp(args.auto_accept)

        print(f"\n{Colors.GREEN}{Colors.BOLD}━━━━━━━━━━━━━━━━━━ Process Complete ━━━━━━━━━━━━━━━━━━{Colors.NC}\n")

    except KeyboardInterrupt:
        print(f"\n\n{Colors.RED}✖ INSTALLATION INTERRUPTED BY USER.{Colors.NC}")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n{Colors.RED}✖ CRITICAL INSTALLATION ERROR: {e}{Colors.NC}")
        sys.exit(1)

if __name__ == "__main__":
    main()