"""``ai server``: the Brain Server (models, agents and web UI over HTTP)."""
from ai.cli.base import SUPPRESS, add_actions, add_command

NAME = "server"
HELP = "Run the Brain Server, relay mode, web UI versions, authenticator setup"
DESCRIPTION = """Serve models, agents and the web UI to other devices.

  ai server                        start the Brain Server (SERVER_HOST:SERVER_PORT)
  ai server --relay URL            run here, send inference to the Brain Server at URL
  ai server totp-setup             create the authenticator secret for risky web tools
  ai server frontend list          cached web UI versions
  ai server frontend use VERSION   pin a version ('bundled' to go back)
"""

DEFAULTS = {"server": False, "relay": None, "modules": [], "frontend": None, "server_totp_setup": False}

LEGACY = {
    "--server": "ai server",
    "--relay": "ai server --relay",
    "--modules": "ai server --modules",
    "--server-totp-setup": "ai server totp-setup",
    "--frontend": "ai server frontend",
}


def register(subparsers, parent):
    parser = add_command(subparsers, NAME, HELP, DESCRIPTION, usage="%(prog)s [--relay URL] [--modules ...]  |  %(prog)s ACTION")
    parser.add_argument("--relay", type=str, metavar="URL",
                        help="Run the server here and send model inference to the Brain Server at URL")
    parser.add_argument("--modules", nargs="+", metavar="MODULE", help="Load specific server sub-modules")
    parser.set_defaults(server=True)

    actions = add_actions(parser, "server_command", required=False)
    totp = add_command(actions, "totp-setup", "Create the authenticator secret that approves risky web agent tools",
                       usage="%(prog)s")
    totp.set_defaults(server=False, server_totp_setup=True)

    frontend = add_command(actions, "frontend", "Web UI versions: list, or use VERSION|bundled",
                           usage="%(prog)s list  |  %(prog)s use VERSION|bundled")
    frontend.add_argument("frontend", nargs="+", metavar="ACTION", help="'list', or 'use VERSION' / 'use bundled'")
    frontend.set_defaults(server=False)


def add_legacy(parser):
    parser.add_argument("--server", action="store_true", help=SUPPRESS)
    parser.add_argument("--relay", type=str, metavar="URL", help=SUPPRESS)
    parser.add_argument("--modules", nargs="+", help=SUPPRESS)
    parser.add_argument("--server-totp-setup", action="store_true", help=SUPPRESS)
    parser.add_argument("--frontend", nargs="+", help=SUPPRESS)


# --- handlers -----------------------------------------------------------------------

def totp_setup(prog, args, directory_manager) -> None:
    """
    Creates (or replaces) the server's TOTP secret and prints it for an authenticator app.
    Run on the server machine: the secret never travels over the network.

    :param args: The parsed command-line arguments.
    :raises SystemExit: Always, after printing the secret.
    """
    import sys
    import ai.functions as func
    from ai.color import Color
    if not getattr(args, "server_totp_setup", False):
        return
    from ai.modules.server.services.auth import AuthService
    from ai.modules.server.services.totp import provisioning_uri

    guard = AuthService().totp
    if guard.enabled:
        answer = input("A TOTP secret already exists; replacing it breaks the current authenticator entry. Replace? (y/N): ")
        if answer.strip().lower() not in ("y", "yes"):
            func.out("Kept the existing secret.")
            sys.exit(0)
    secret = guard.setup()
    func.out(f"{Color.GREEN}TOTP enabled.{Color.RESET} Add it to your authenticator app:")
    func.out(f"  secret: {secret}")
    func.out(f"  uri:    {provisioning_uri(secret)}")
    try:
        import qrcode  # optional: shows a scannable code when installed
        qr = qrcode.QRCode(border=1)
        qr.add_data(provisioning_uri(secret))
        qr.print_ascii(invert=True)
    except ImportError:
        pass
    func.out(f"Stored in {guard.path} (mode 600).")
    func.out('Codes are required only when "SERVER_TOTP_ENABLED": true is set in config.json (restart the server after).')
    sys.exit(0)


def frontend(prog, args, directory_manager) -> None:
    """
    ``--frontend list``: the bundled, cached and active frontend versions.
    ``--frontend use <version>|bundled``: pins SERVER_FRONTEND_VERSION in config.json.

    :param args: The parsed command-line arguments.
    :raises SystemExit: Always, after the command.
    """
    import os
    import sys
    import ai.functions as func
    from ai.services.directory_manager import DirectoryManager
    command = getattr(args, "frontend", None)
    if not command:
        return
    import json as _json
    from ai.modules.server.services import frontend as fe

    config_path = os.path.join(DirectoryManager().get_root_dir(), "config.json")
    with open(config_path, encoding="utf-8") as f:
        settings = _json.load(f)
    pinned = settings.get("SERVER_FRONTEND_VERSION") or "bundled"

    if command[0] == "list":
        bundled = None
        if fe.BUNDLED_TAR.is_file():
            try:
                bundled = fe.archive_version(fe.BUNDLED_TAR).get("version")
            except Exception as e:
                func.out(f"Bundled frontend unreadable: {e}")
        func.out(f"Bundled: {bundled or 'none'}   Pinned: {pinned}   Server api_level: {fe.API_LEVEL}")
        for entry in fe.cached_versions():
            marks = []
            if entry["version"] == bundled:
                marks.append("bundled")
            if entry["version"] == pinned:
                marks.append("pinned")
            level = entry["api_level"] if entry["api_level"] is not None else "?"
            func.out(f"  {entry['version']:<12} api_level {level:<3} {entry['built_at'] or ''}  {' '.join(marks)}")
        sys.exit(0)

    if command[0] == "use" and len(command) == 2:
        version = command[1]
        if version != "bundled":
            folder = fe.cache_root() / version
            if not (folder / "index.html").is_file():
                func.error(f"Frontend {version} is not in the cache. See: ai server frontend list")
                sys.exit(1)
            level = fe.read_version(folder).get("api_level") or 0
            if int(level) > fe.API_LEVEL:
                func.error(f"Frontend {version} needs api_level {level}; this server has {fe.API_LEVEL}.")
                sys.exit(1)
        if version == "bundled":
            settings.pop("SERVER_FRONTEND_VERSION", None)
        else:
            settings["SERVER_FRONTEND_VERSION"] = version
        with open(config_path, "w", encoding="utf-8") as f:
            _json.dump(settings, f, indent=4)
        func.out(f"Frontend set to {version}. Restart the server to apply.")
        sys.exit(0)

    func.error("Usage: ai server frontend list | ai server frontend use <version>|bundled")
    sys.exit(1)


MAINTENANCE = (totp_setup, frontend)
