import subprocess
import os
import sys
import argparse

# Global flag to control auto-acceptance
AUTO_ACCEPT_MODE = False

# ANSI escape codes for colors
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m' # Resets the color
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def get_user_confirmation(prompt):
    """
    Asks the user for confirmation and returns True if 'y' or 'Y', False otherwise.
    If AUTO_ACCEPT_MODE is True, it automatically returns True.
    """
    if AUTO_ACCEPT_MODE:
        print(f"{Colors.CYAN}{prompt} (Auto-accepting due to --auto-accept flag).{Colors.ENDC}")
        return True
    
    while True:
        response = input(f"{Colors.BLUE}{prompt} (y/n): {Colors.ENDC}").strip().lower()
        if response in ['y', 'yes']:
            return True
        elif response in ['n', 'no']:
            return False
        else:
            print(f"{Colors.WARNING}Invalid input. Please enter 'y' or 'n'.{Colors.ENDC}")

def install_requirements_txt():
    """
    Installs dependencies from requirements.txt using pip.
    """
    print(f"\n{Colors.HEADER}--- Step 1: Installing dependencies from requirements.txt ---{Colors.ENDC}")
    if get_user_confirmation("Do you want to install dependencies from 'requirements.txt'?"):
        try:
            print(f"{Colors.CYAN}Running: pip install --upgrade pip{Colors.ENDC}")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"])
            print(f"{Colors.CYAN}Running: pip install -r requirements.txt{Colors.ENDC}")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
            print(f"{Colors.GREEN}Successfully installed dependencies from requirements.txt.{Colors.ENDC}")
        except FileNotFoundError:
            print(f"{Colors.FAIL}Error: 'requirements.txt' not found in the current directory.{Colors.ENDC}")
            print(f"{Colors.WARNING}Please make sure 'requirements.txt' is in the same directory as this script.{Colors.ENDC}")
        except subprocess.CalledProcessError as e:
            print(f"{Colors.FAIL}Error installing dependencies from requirements.txt: {e}{Colors.ENDC}")
            print(f"{Colors.WARNING}Please check the error message above for details.{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.FAIL}An unexpected error occurred during requirements.txt installation: {e}{Colors.ENDC}")
    else:
        print(f"{Colors.WARNING}Skipping installation from requirements.txt.{Colors.ENDC}")

def install_llama_cpp_python():
    """
    Installs llama-cpp-python with specific CMAKE_ARGS environment variables.
    """
    print(f"\n{Colors.HEADER}--- Step 2: Installing llama-cpp-python with CUDA support ---{Colors.ENDC}")
    print(f"{Colors.CYAN}This step involves setting specific environment variables for CUDA compilation.{Colors.ENDC}")
    print(f"{Colors.CYAN}Command to be run:{Colors.ENDC}")
    print(f'{Colors.BOLD}CMAKE_ARGS="-DGGML_CUDA=on -DGGML_CUDA_FORCE_CUBLAS=on -DLLAVA_BUILD=off -DCMAKE_CUDA_ARCHITECTURES=native" FORCE_CMAKE=1 pip install llama-cpp-python --no-cache-dir --force-reinstall --upgrade{Colors.ENDC}')

    if get_user_confirmation("Do you want to proceed with installing llama-cpp-python with these arguments?"):
        env = os.environ.copy()
        env["CMAKE_ARGS"] = "-DGGML_CUDA=on -DGGML_CUDA_FORCE_CUBLAS=on -DLLAVA_BUILD=off -DCMAKE_CUDA_ARCHITECTURES=native"
        env["FORCE_CMAKE"] = "1"

        try:
            print(f"{Colors.CYAN}Running pip install for llama-cpp-python...{Colors.ENDC}")
            subprocess.check_call([
                sys.executable, "-m", "pip", "install",
                "llama-cpp-python",
                "--no-cache-dir",
                "--force-reinstall",
                "--upgrade"
            ], env=env)
            print(f"{Colors.GREEN}Successfully installed llama-cpp-python.{Colors.ENDC}")
        except subprocess.CalledProcessError as e:
            print(f"{Colors.FAIL}Error installing llama-cpp-python: {e}{Colors.ENDC}")
            print(f"{Colors.WARNING}Please ensure you have the necessary CUDA toolkit and development tools installed if you are building with CUDA.{Colors.ENDC}")
        except Exception as e:
            print(f"{Colors.FAIL}An unexpected error occurred during llama-cpp-python installation: {e}{Colors.ENDC}")
    else:
        print(f"{Colors.WARNING}Skipping llama-cpp-python installation.{Colors.ENDC}")

def main(auto_accept=False):
    """
    Main function to orchestrate the installation process.
    Can be called with auto_accept=True to bypass prompts.
    """
    global AUTO_ACCEPT_MODE
    AUTO_ACCEPT_MODE = auto_accept

    if AUTO_ACCEPT_MODE:
        print(f"{Colors.BOLD}{Colors.CYAN}Auto-accept mode enabled. All prompts will be automatically confirmed.{Colors.ENDC}")

    print(f"{Colors.HEADER}{Colors.BOLD}Welcome to the Python Dependency Installer!{Colors.ENDC}")

    install_requirements_txt()
    install_llama_cpp_python()

    print(f"\n{Colors.GREEN}{Colors.BOLD}Installation process completed.{Colors.ENDC}")
    print(f"{Colors.BLUE}Please check the output above for any errors or warnings.{Colors.ENDC}")

if __name__ == "__main__":
    # This block is only executed when dependency_installer.py is run directly
    parser = argparse.ArgumentParser(description="Python Dependency Installer Script.")
    parser.add_argument(
        "--auto-accept",
        "-y",
        action="store_true",
        help="Automatically accept all installation prompts."
    )
    args = parser.parse_args()
    main(auto_accept=args.auto_accept)
