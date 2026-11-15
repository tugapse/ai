"""The command line: sub-commands and the old flags fill the same ``args``."""
import io

import pytest

from ai.cli import _legacy_used, all_defaults, parse_args, warn_legacy


def parse(*argv):
    return parse_args(list(argv), warn=False)[1]


@pytest.mark.parametrize("new,old", [
    (["agent", "-m", "x"], ["--agent", "-m", "x"]),
    (["agent", "--resume", "3f"], ["--resume", "3f"]),
    (["agent", "--pipeline", "small", "-m", "x"], ["--agent", "--pipeline", "small", "-m", "x"]),
    (["agent", "--knowledge", "a", "--knowledge", "b"], ["--agent", "-kb", "a", "-kb", "b"]),
    (["sessions", "list"], ["--list-sessions"]),
    (["server"], ["--server"]),
    (["server", "--relay", "http://gpu:9999"], ["--relay", "http://gpu:9999"]),
    (["server", "totp-setup"], ["--server-totp-setup"]),
    (["server", "frontend", "use", "0.1.0"], ["--frontend", "use", "0.1.0"]),
    (["knowledge", "build"], ["--build-knowledge"]),
    (["knowledge", "build", "src", "--mode", "all", "--ext", "py,ts", "--max", "3", "--force"],
     ["--build-knowledge", "src", "--kb-mode", "all", "--kb-ext", "py,ts", "--kb-max", "3", "--kb-force"]),
    (["knowledge", "list"], ["--knowledge-list"]),
    (["knowledge", "forget", "abc"], ["--knowledge-forget", "abc"]),
    (["models", "list"], ["-l"]),
    (["models", "generate", "mine", "--type", "gguf"], ["--generate-config", "mine", "--model-type", "gguf"]),
    (["tools", "create", "git_status"], ["--create-tool", "git_status"]),
    (["install"], ["--install"]),
    (["config", "reset"], ["--overwrite-config"]),
])
def test_new_and_old_forms_match(new, old):
    a, b = vars(parse(*new)), vars(parse(*old))
    # --resume and --relay imply agent / server mode in the dispatcher (cli_args), not in args
    implied = {"agent"} if old[0] == "--resume" else {"server"} if old[0] == "--relay" else set()
    ignore = implied | {"command", "sessions_command", "server_command", "knowledge_command", "models_command",
              "tools_command", "config_command"}
    assert {k: v for k, v in a.items() if k not in ignore} == {k: v for k, v in b.items() if k not in ignore}


def test_every_default_is_present():
    args = parse()
    for key, value in all_defaults().items():
        assert getattr(args, key) == value


def test_value_before_the_command_is_kept():
    args = parse("-m", "hi", "-md", "agents/lite", "agent")
    assert (args.agent, args.msg, args.model) == (True, "hi", "agents/lite")


def test_defaults_are_not_shared_between_runs():
    parse().modules.append("x")
    assert parse().modules == []


def test_subcommand_flags_are_not_reported_as_legacy():
    assert _legacy_used(["agent", "--pipeline", "small"], "agent") == []
    assert _legacy_used(["--agent", "--pipeline", "small"], None) == ["--agent", "--pipeline"]
    assert _legacy_used(["--relay=http://x"], None) == ["--relay"]


def test_legacy_notice_names_the_new_form():
    stream = io.StringIO()
    warn_legacy(["--server", "-l"], stream)
    text = stream.getvalue()
    assert "--server -> ai server" in text and "-l -> ai models list" in text


def test_server_actions_do_not_start_the_server():
    assert parse("server", "totp-setup").server is False
    assert parse("server", "frontend", "list").server is False
    assert parse("server").server is True


def test_mcp_command():
    assert (parse("mcp", "list").mcp_action, parse("mcp", "list").mcp_server) == ("list", None)
    args = parse("mcp", "enable", "playwright")
    assert (args.mcp_action, args.mcp_server) == ("enable", "playwright")
