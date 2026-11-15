"""``ai models``: list model configs and write new ones."""
from ai.cli.base import SUPPRESS, add_actions, add_command
from ai.entities.model_enums import ModelType

NAME = "models"
HELP = "List the model configs or generate a new one"
DESCRIPTION = """Model configs live in user/models/ (yours, win) and system/models/ (shipped).

  ai models list                       what's available
  ai models generate NAME --type gguf  write a starting config to user/models/
  ai -md agents/lite -m "hi"           use one for a run
"""

DEFAULTS = {"list_models": False, "generate_config": None, "model_type": None}

LEGACY = {
    "--list-models": "ai models list", "-l": "ai models list",
    "--generate-config": "ai models generate", "--model-type": "ai models generate NAME --type",
}

_TYPES = [t.value for t in ModelType]


def register(subparsers, parent):
    parser = add_command(subparsers, NAME, HELP, DESCRIPTION, usage="%(prog)s ACTION")
    actions = add_actions(parser, "models_command")
    add_command(actions, "list", "List the available model configs", usage="%(prog)s").set_defaults(list_models=True)

    generate = add_command(actions, "generate", "Write a new model config to user/models/",
                           usage="%(prog)s NAME --type TYPE")
    generate.add_argument("generate_config", metavar="NAME", help="File name (.json optional)")
    generate.add_argument("--type", dest="model_type", choices=_TYPES, required=True, help="Provider type")


def add_legacy(parser):
    parser.add_argument("--list-models", "-l", action="store_true", help=SUPPRESS)
    parser.add_argument("--generate-config", metavar="FILENAME", type=str, help=SUPPRESS)
    parser.add_argument("--model-type", type=str, choices=_TYPES, help=SUPPRESS)


def list_models(out=None) -> int:
    """
    Prints every model config: user/models/ first (they win), then system/models/.
    A system config hidden by a user one with the same name is marked. Returns how many were listed.
    """
    import json
    import os

    import ai.functions as func
    from ai.color import Color
    from ai.services.model_orchestrator import ModelOrchestrator

    out = out or func.out
    folders = ModelOrchestrator.config_folders()          # [user, system]
    labels = ["user", "system"]
    seen = set()
    count = 0
    for label, folder in zip(labels, folders):
        rows = []
        for root, _dirs, files in os.walk(folder):
            for name in sorted(files):
                if not name.endswith(".json"):
                    continue
                path = os.path.join(root, name)
                key = os.path.relpath(path, folder)[:-5].replace(os.sep, "/")
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    detail = f"{data.get('model_type', '?')}  {data.get('model_name', '')}"
                except Exception as e:
                    detail = f"{Color.RED}unreadable: {e}{Color.RESET}"
                hidden = f"  {Color.DIM}(hidden by user/models){Color.RESET}" if key in seen else ""
                rows.append((key, detail, hidden))
                seen.add(key)
        out(f"{Color.CYAN}{label}/models{Color.RESET}  {Color.DIM}{folder}{Color.RESET}")
        if not rows:
            out("  (none)")
        width = max((len(k) for k, _, _ in rows), default=0)
        for key, detail, hidden in sorted(rows):
            out(f"  {key.ljust(width)}  {detail}{hidden}")
            count += 1
    out("\nUse one with: ai -md NAME ...   (default: MODEL_CONFIG_NAME in config.json)")
    return count


# --- handlers -----------------------------------------------------------------------

def generate_config(prog, args, directory_manager) -> None:
    """
    Generates a default model configuration file based on user input.

    :param prog: The main program instance.
    :param args: The parsed arguments containing configuration generation flags.
    :param parser: The argument parser instance, used for error reporting.
    :param directory_manager: The directory management service.
    :raises SystemExit: Exits after successfully generating the config or upon failure.
    """
    import os
    import sys
    import ai.functions as func
    from ai.color import Color, format_text
    from ai.model_config_manager import ModelConfigManager
    from ai.entities.model_enums import ModelType
    if not args.generate_config:
        return

    if not args.model_type:
        func.error("Generating a model config needs a type: ai models generate NAME --type TYPE")
        sys.exit(2)

    try:
        model_type_enum = ModelType(args.model_type)
        config_filename = args.generate_config if args.generate_config.endswith(".json") else f"{args.generate_config}.json"

        models_dir = directory_manager.get_user_models_directory()
        func.ensure_directory_exists(models_dir)

        full_filepath = os.path.join(models_dir, config_filename)
        new_config = ModelConfigManager.generate_default_config(model_name=args.generate_config, model_type=model_type_enum)

        ModelConfigManager.save_config(new_config, full_filepath) 
        print(format_text(f"\nConfiguration saved to: {full_filepath}", Color.GREEN))
    except Exception as e:
        func.error(f"Config generation failed: {e}")
    sys.exit(0)


def list_command(prog, args, directory_manager) -> None:
    """
    Lists the available model configs (user/models/ then system/models/).

    :param args: The parsed arguments containing the --list-models flag.
    :raises SystemExit: Exits after displaying the status message.
    """
    import sys
    if args.list_models:
        from ai.cli.models import list_models
        list_models()
        sys.exit(0)


MAINTENANCE = (generate_config, list_command)
