import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


def find_virtual_environment(executable_dir: Path) -> Optional[Path]:
    configured_venv = os.environ.get("AI_VENV_PATH")
    if configured_venv:
        venv = Path(configured_venv).resolve()
        if (venv / "Scripts" / "python.exe").is_file():
            return venv
        return None

    for directory in (executable_dir, executable_dir.parent):
        venv = directory / ".venv"
        if (venv / "Scripts" / "python.exe").is_file():
            return venv
    return None


def main() -> int:
    executable_dir = Path(sys.executable).resolve().parent
    bundle_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    script_path = bundle_dir / "run.ps1"

    if not script_path.is_file() or not (bundle_dir / "src" / "ai" / "main.py").is_file():
        print(
            "The packaged application files are missing from this executable.",
            file=sys.stderr,
        )
        return 1

    venv_dir = find_virtual_environment(executable_dir)
    if venv_dir is None:
        print(
            "Could not find a Python virtual environment. Place the project "
            ".venv folder beside ai.exe, or set AI_VENV_PATH to its location.",
            file=sys.stderr,
        )
        return 1

    powershell = shutil.which("powershell.exe")
    if powershell is None:
        print("Windows PowerShell (powershell.exe) was not found.", file=sys.stderr)
        return 1

    child_env = os.environ.copy()
    child_env["AI_PROJECT_ROOT"] = str(bundle_dir)
    child_env["AI_VENV_PATH"] = str(venv_dir)
    engine_status_path = executable_dir / "installed_engines.json"
    bundled_status_path = bundle_dir / "installed_engines.json"
    if not engine_status_path.exists() and bundled_status_path.is_file():
        try:
            shutil.copy2(bundled_status_path, engine_status_path)
        except OSError as error:
            print(
                f"Could not initialize engine status file '{engine_status_path}': {error}",
                file=sys.stderr,
            )
            return 1
    child_env["AI_ENGINE_STATUS_FILE"] = str(engine_status_path)
    result = subprocess.run(
        [
            powershell,
            "-NoProfile",
            "-File",
            str(script_path),
            *sys.argv[1:],
        ],
        cwd=executable_dir,
        env=child_env,
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
