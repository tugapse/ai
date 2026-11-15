"""``ai install`` and ``ai config``: optional engines and the AI folder's config."""
from ai.cli.base import SUPPRESS, add_actions, add_command

DEFAULTS = {"install": False, "overwrite_config": False}

LEGACY = {"--install": "ai install", "--overwrite-config": "ai config reset"}


def register(subparsers, parent):
    add_command(subparsers, "install", "Install or remove optional engines (GGUF, Ollama, server, memory, voice...)",
                "Opens the engine menu. What's installed is recorded in installed_engines.json.",
                usage="%(prog)s").set_defaults(install=True)

    config = add_command(subparsers, "config", "Reset the config of the AI folder",
                         """The AI folder is AI_ASSISTANT_DIRECTORY (default ~/Ai).

  ai config reset                  reset config.json to the defaults (your settings are lost)
                                   and copy missing template files; existing templates are kept
""", usage="%(prog)s ACTION")
    actions = add_actions(config, "config_command")
    add_command(actions, "reset", "Reset config.json to the defaults and copy missing templates",
                usage="%(prog)s").set_defaults(overwrite_config=True)


def add_legacy(parser):
    parser.add_argument("--install", action="store_true", help=SUPPRESS)
    parser.add_argument("--overwrite-config", action="store_true", help=SUPPRESS)


# --- handlers -----------------------------------------------------------------------

def install(prog, args, directory_manager) -> None:
    """
    Handles the installation or updating of necessary engine components.

    :param args: The parsed arguments containing the --install flag.
    :raises FileNotFoundError: If required installer or virtual environment files are missing.
    :raises ImportError: If the installer module cannot be loaded.
    :raises SystemExit: Exits after installation is complete or if an error occurs.
    """
    import sys
    import subprocess
    from pathlib import Path
    import ai.functions as func
    if args.install:
        import importlib.util
        if getattr(sys, "frozen", False):
            project_root = Path(sys.executable).resolve().parent.parent
        else:
            project_root = Path(__file__).resolve().parents[3]  # src/ai/cli/setup.py -> repo root

        installer_path = project_root / "scripts" / "install_engines.py"
        if not installer_path.is_file():
            raise FileNotFoundError(
                f"Engine installer not found at '{installer_path}'. "
                "Run 'ai install' from the project checkout."
            )

        if getattr(sys, "frozen", False):
            venv_python = project_root / ".venv" / "Scripts" / "python.exe"
            if not venv_python.is_file():
                raise FileNotFoundError(
                    f"Project virtual environment not found at '{venv_python}'. "
                    "Run .\\build.ps1 from the project checkout first."
                )
            subprocess.run(
                [str(venv_python), str(installer_path)],
                cwd=project_root,
                check=True,
            )
            func.out(
                "Engine installation updated the project environment. "
                "Run .\\compile.ps1 to include changes in the executable."
            )
            sys.exit(0)

        spec = importlib.util.spec_from_file_location("install_engines", installer_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not load engine installer from '{installer_path}'.")

        installer_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(installer_module)
        installer_module.main_menu()
        sys.exit(0)


MAINTENANCE = (install,)
