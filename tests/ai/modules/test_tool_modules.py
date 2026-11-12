"""Built-in tools as app modules (ai.modules.tools_*) and the new tools."""

import os
from unittest.mock import MagicMock

import pytest

import ai.program  # noqa: F401  (startup import order, avoids a circular import)
from ai.config import ProgramSetting
from ai.modules.base_module import ToolModule
from ai.services.module_registry import ModuleRegistry
from ai.tools import base

ALL_TOOLS = {
    "read_dir", "read_file", "read_files", "write_file", "patch_file", "delete_file",
    "smart_search", "grep_file", "execute_command",
    "web_search", "web_read", "send_notification",
}


class FakeConfig:
    def __init__(self, values=None):
        self.values = values or {}

    def get(self, key, default=None):
        return self.values.get(str(key), default)


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.setattr(base, "PROJECT_ROOT", str(tmp_path))
    return tmp_path


# ---------------------------------------------------------------- structure

class TestModules:
    def test_all_tool_modules_load_by_default(self):
        registry = ModuleRegistry(FakeConfig())
        registry.load_all()
        for name in ModuleRegistry.TOOL_MODULES:
            assert isinstance(registry[name], ToolModule), name
        assert set(registry.tool_functions()) == ALL_TOOLS
        assert registry["voice"] is None and registry["vector_memory"] is None  # still opt-in

    @pytest.mark.parametrize("value", [False, "false", "0", "off"])
    def test_module_can_be_disabled_in_config(self, value):
        registry = ModuleRegistry(FakeConfig({"TOOLS_WEB_ENABLED": value, "TOOLS_SHELL_ENABLED": value}))
        registry.load_all()
        tools = registry.tool_functions()
        assert registry["tools_web"] is None and registry["tools_shell"] is None
        assert not {"web_search", "web_read", "execute_command"} & set(tools)
        assert "read_file" in tools

    def test_setting_keys_exist_for_cli_modules_flag(self):
        for name in ModuleRegistry.TOOL_MODULES:
            assert ProgramSetting(f"{name.upper()}_ENABLED")

    def test_tool_module_lifecycle(self):
        from ai.modules import tools_search
        module = tools_search.create_module()
        assert module.get_instance() is module  # lazily initialized
        assert module.tool_names == ["smart_search", "grep_file"]
        module.shutdown()
        assert module.tools.get_tools() == {}

    def test_orchestrator_picks_up_module_tools(self, tmp_path, monkeypatch):
        from ai.agents.agent_orchestrator import AgentOrchestrator, MCPBridge
        from ai.agents.agent_io import AgentIO
        from ai.tools.tool_registry import ToolRegistry
        monkeypatch.setattr(MCPBridge, "load_from_config", lambda self, p: None)

        modules = ModuleRegistry(FakeConfig({"TOOLS_NOTIFY_ENABLED": False}))
        modules.load_all()
        tool_registry = ToolRegistry()
        tool_registry.get_all_tools().pop("send_notification", None)
        orch = AgentOrchestrator(llm_connector=MagicMock(get_context_limit=lambda: 8000, get_max_tokens=lambda: 100),
                                 tool_registry=tool_registry,
                                 pipeline_config={"agents": {"MASTER": {"tools": []}}},
                                 module_registry=modules, io=AgentIO())
        orch._initialize_modules()
        registered = set(tool_registry.get_all_tools())
        assert ALL_TOOLS - {"send_notification"} <= registered
        assert "send_notification" not in registered
        orch.close()

    def test_compat_shim(self, project):
        import ai.tools.agent_tools as agent_tools
        assert set(agent_tools.AVAILABLE_TOOLS) == ALL_TOOLS
        assert agent_tools.PROJECT_ROOT == str(project)
        agent_tools.PROJECT_ROOT = "/somewhere/else"
        assert base.PROJECT_ROOT == "/somewhere/else"
        from ai.tools.agent_tools import tool, _resolve_path  # old imports keep working
        assert callable(tool) and callable(_resolve_path)


# ---------------------------------------------------------------- filesystem

class TestFilesystemTools:
    def test_read_files(self, project):
        from ai.modules.tools_filesystem.tools import read_files
        (project / "a.txt").write_text("A")
        (project / "b.txt").write_text("B")
        result = read_files(paths=["a.txt", "@ROOT/b.txt"])
        assert result == {"status": "SUCCESS", "files": {"@ROOT/a.txt": "A", "@ROOT/b.txt": "B"}}

    def test_read_files_reports_missing(self, project):
        from ai.modules.tools_filesystem.tools import read_files
        (project / "a.txt").write_text("A")
        result = read_files(paths=["a.txt", "nope.txt"])
        assert result["status"] == "FAILED" and result["files"]["@ROOT/a.txt"] == "A"
        assert "nope.txt" in result["files"]
        assert read_files()["status"] == "FAILED"

    def test_delete_file(self, project):
        from ai.modules.tools_filesystem.tools import delete_file
        target = project / "old.log"
        target.write_text("x")
        assert delete_file(path="@ROOT/old.log") == {"status": "SUCCESS", "path": "@ROOT/old.log"}
        assert not target.exists()

    def test_delete_empty_dir_only(self, project):
        from ai.modules.tools_filesystem.tools import delete_file
        (project / "empty").mkdir()
        (project / "full").mkdir()
        (project / "full" / "f").write_text("x")
        assert delete_file(path="empty")["status"] == "SUCCESS"
        result = delete_file(path="full")
        assert result["status"] == "FAILED" and "not empty" in result["error"]
        assert (project / "full" / "f").exists()

    @pytest.mark.parametrize("path, message", [
        ("@ROOT", "project root"),
        (".", "project root"),
        ("../outside.txt", "outside project"),
        ("missing.txt", "No such file"),
    ])
    def test_delete_refusals(self, project, path, message):
        from ai.modules.tools_filesystem.tools import delete_file
        result = delete_file(path=path)
        assert result["status"] == "FAILED" and message in result["error"]

    def test_delete_requires_approval_by_default(self):
        from ai.agents.agent_orchestrator import get_hil_tools
        assert "delete_file" in get_hil_tools()


# ---------------------------------------------------------------- grep_file

CODE = "\n".join([
    "import os",            # 1
    "",                     # 2
    "def alpha():",         # 3
    "    return 1",         # 4
    "",                     # 5
    "def beta():",          # 6
    "    return 2",         # 7
    "",                     # 8
    "class Alpha:",         # 9
    "    pass",             # 10
])


class TestGrepFile:
    @pytest.fixture
    def code_file(self, project):
        (project / "m.py").write_text(CODE)
        return "@ROOT/m.py"

    def test_matches_with_context(self, code_file):
        from ai.modules.tools_search.tools import grep_file
        result = grep_file(path=code_file, pattern=r"def \w+", context=1)
        assert result["status"] == "SUCCESS" and result["total_matches"] == 2
        assert result["output"].splitlines() == ["2-", "3:def alpha():", "4-    return 1", "5-", "6:def beta():", "7-    return 2"]

    def test_separate_blocks_and_case(self, code_file):
        from ai.modules.tools_search.tools import grep_file
        result = grep_file(path=code_file, pattern="alpha", context=0)
        assert result["output"].splitlines() == ["3:def alpha():", "--", "9:class Alpha:"]
        strict = grep_file(path=code_file, pattern="alpha", context=0, ignore_case="false")
        assert strict["total_matches"] == 1

    def test_invalid_regex_falls_back_to_literal(self, project):
        from ai.modules.tools_search.tools import grep_file
        (project / "x.txt").write_text("call foo(bar\nother")
        result = grep_file(path="x.txt", pattern="foo(bar", context=0)
        assert result["output"] == "1:call foo(bar"

    def test_max_matches(self, project):
        from ai.modules.tools_search.tools import grep_file
        (project / "many.txt").write_text("\n".join("hit" for _ in range(10)))
        result = grep_file(path="many.txt", pattern="hit", context=0, max_matches=3)
        assert result["total_matches"] == 10 and "7 more matches" in result["output"]

    def test_errors(self, project):
        from ai.modules.tools_search.tools import grep_file
        assert grep_file(path="none.py", pattern="x")["status"] == "FAILED"
        assert grep_file(path="none.py")["status"] == "FAILED"
        (project / "e.txt").write_text("abc")
        assert grep_file(path="e.txt", pattern="zzz")["output"] == "No matches."


# ---------------------------------------------------------------- web

DDG_HTML = """
<html><body>
<div class="result results_links results_links_deep result--ad">
  <a class="result__a" href="https://duckduckgo.com/y.js?ad_provider=x">Sponsored thing</a>
  <a class="result__snippet">Buy now</a>
</div>
<div class="result results_links results_links_deep web-result">
  <h2 class="result__title"><a rel="nofollow" class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fdocs.python.org%2F3%2Flibrary%2Fasyncio.html&amp;rut=abc">asyncio &mdash; Asynchronous I/O</a></h2>
  <a class="result__snippet" href="#">asyncio is a library to write <b>concurrent</b> code.</a>
</div>
<div class="result results_links results_links_deep web-result">
  <h2 class="result__title"><a class="result__a" href="https://realpython.com/async-io-python/">Async IO in Python</a></h2>
  <div class="result__snippet">A complete walkthrough.</div>
</div>
</body></html>
"""

PAGE_HTML = """<html><head><title>My  Test &amp; Page</title><style>.x{color:red}</style>
<script>var secret = 1;</script></head>
<body><nav>Home</nav><h1>Main Title</h1><p>First paragraph with <a href="/x">a link</a>.</p>
<ul><li>one</li><li>two</li></ul><noscript>enable js</noscript><h2>Section</h2><p>More   text.</p></body></html>"""


class FakeResponse:
    def __init__(self, text="", status=200, content_type="text/html; charset=utf-8", url="https://example.com/page"):
        self.text = text
        self.status_code = status
        self.headers = {"Content-Type": content_type}
        self.url = url
        self.encoding = "utf-8"

    def iter_content(self, size):
        data = self.text.encode()
        for i in range(0, len(data), size):
            yield data[i:i + size]

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


@pytest.fixture
def fake_requests(monkeypatch):
    from ai.modules.tools_web import tools as web
    fake = MagicMock()
    monkeypatch.setattr(web, "_requests", lambda: fake)
    return fake


class TestWebSearch:
    def test_parses_results_skipping_ads(self, fake_requests):
        from ai.modules.tools_web.tools import web_search
        fake_requests.post.return_value = FakeResponse(DDG_HTML)
        result = web_search(query="python asyncio", max_results="5")
        assert result["status"] == "SUCCESS"
        assert result["results"] == [
            {"title": "asyncio — Asynchronous I/O", "url": "https://docs.python.org/3/library/asyncio.html",
             "snippet": "asyncio is a library to write concurrent code."},
            {"title": "Async IO in Python", "url": "https://realpython.com/async-io-python/", "snippet": "A complete walkthrough."},
        ]
        assert fake_requests.post.call_args.kwargs["data"]["q"] == "python asyncio"

    def test_max_results_and_region(self, fake_requests):
        from ai.modules.tools_web.tools import web_search
        fake_requests.post.return_value = FakeResponse(DDG_HTML)
        result = web_search(query="x", max_results=1, region="pt-pt")
        assert len(result["results"]) == 1
        assert fake_requests.post.call_args.kwargs["data"]["kl"] == "pt-pt"

    def test_bot_check_and_errors(self, fake_requests):
        from ai.modules.tools_web.tools import web_search
        fake_requests.post.return_value = FakeResponse("<html>anomaly detected, captcha</html>")
        assert "bot check" in web_search(query="x")["error"]
        fake_requests.post.return_value = FakeResponse("", status=503)
        assert "503" in web_search(query="x")["error"]
        fake_requests.post.side_effect = OSError("network down")
        assert "network down" in web_search(query="x")["error"]
        assert web_search()["status"] == "FAILED"

    def test_no_results(self, fake_requests):
        from ai.modules.tools_web.tools import web_search
        fake_requests.post.return_value = FakeResponse("<html><body>No results.</body></html>")
        result = web_search(query="qwzxv")
        assert result["status"] == "SUCCESS" and result["results"] == []


class TestWebRead:
    def test_html_to_clean_text(self, fake_requests):
        from ai.modules.tools_web.tools import web_read
        fake_requests.get.return_value = FakeResponse(PAGE_HTML)
        result = web_read(url="https://example.com/page")
        assert result["status"] == "SUCCESS"
        assert result["title"] == "My Test & Page"
        content = result["content"]
        assert "# Main Title" in content and "## Section" in content
        assert "First paragraph with a link." in content
        assert "- one" in content and "- two" in content
        assert "More text." in content
        for hidden in ("secret", "color:red", "enable js"):
            assert hidden not in content
        assert result["truncated"] is False

    def test_truncation(self, fake_requests):
        from ai.modules.tools_web.tools import web_read
        fake_requests.get.return_value = FakeResponse("<p>" + "word " * 2000 + "</p>")
        result = web_read(url="https://e.com", max_chars=600)
        assert len(result["content"]) == 600 and result["truncated"] is True and result["total_chars"] > 600

    def test_plain_text_and_json(self, fake_requests):
        from ai.modules.tools_web.tools import web_read
        fake_requests.get.return_value = FakeResponse('{"a": 1}', content_type="application/json")
        assert web_read(url="https://api.e.com/x")["content"] == '{"a": 1}'

    def test_refusals(self, fake_requests):
        from ai.modules.tools_web.tools import web_read
        fake_requests.get.return_value = FakeResponse("PK..", content_type="application/zip")
        assert "Unsupported content type" in web_read(url="https://e.com/f.zip")["error"]
        assert web_read(url="file:///etc/passwd")["status"] == "FAILED"
        assert web_read(url="ftp://e.com")["status"] == "FAILED"
        assert web_read()["status"] == "FAILED"
        fake_requests.get.return_value = FakeResponse("nope", status=404)
        assert "404" in web_read(url="https://e.com/missing")["error"]

    def test_bare_domain_gets_https(self, fake_requests):
        from ai.modules.tools_web.tools import web_read
        fake_requests.get.return_value = FakeResponse("<p>hi</p>")
        web_read(url="example.com/docs")
        assert fake_requests.get.call_args.args[0] == "https://example.com/docs"


# ---------------------------------------------------------------- notifications

class TestSendNotification:
    @pytest.fixture
    def linux(self, monkeypatch):
        from ai.modules.tools_notify import tools as notify
        monkeypatch.setattr(notify.sys, "platform", "linux")
        monkeypatch.setattr(notify.shutil, "which", lambda name: f"/usr/bin/{name}")
        run = MagicMock(return_value=MagicMock(returncode=0, stderr="", stdout=""))
        monkeypatch.setattr(notify.subprocess, "run", run)
        return run

    def test_linux_notify_send_with_args_list(self, linux):
        from ai.modules.tools_notify.tools import send_notification
        result = send_notification(title="Build", message='Done; rm -rf / "quoted"', urgency="critical")
        assert result == {"status": "SUCCESS", "method": "notify-send"}
        cmd = linux.call_args.args[0]
        assert cmd == ["notify-send", "--app-name=JARVIS", "--urgency=critical", "Build", 'Done; rm -rf / "quoted"']

    def test_defaults_and_validation(self, linux):
        from ai.modules.tools_notify.tools import send_notification
        send_notification(message="hi", urgency="extreme")
        assert linux.call_args.args[0][2:] == ["--urgency=normal", "JARVIS", "hi"]
        assert send_notification()["status"] == "FAILED"

    def test_notifier_failure(self, linux):
        from ai.modules.tools_notify.tools import send_notification
        linux.return_value = MagicMock(returncode=1, stderr="Cannot autolaunch D-Bus", stdout="")
        result = send_notification(message="hi")
        assert result["status"] == "FAILED" and "D-Bus" in result["error"]

    def test_macos_escapes_quotes(self, monkeypatch):
        from ai.modules.tools_notify import tools as notify
        monkeypatch.setattr(notify.sys, "platform", "darwin")
        monkeypatch.setattr(notify.shutil, "which", lambda name: "/usr/bin/osascript" if name == "osascript" else None)
        cmd = notify._notify_command('T"1', 'say "hi"', "normal")
        assert cmd[:2] == ["osascript", "-e"] and 'say \\"hi\\"' in cmd[2]

    def test_no_notifier_falls_back_to_bell(self, monkeypatch):
        from ai.modules.tools_notify import tools as notify
        monkeypatch.setattr(notify.sys, "platform", "linux")
        monkeypatch.setattr(notify.shutil, "which", lambda name: None)
        result = notify.send_notification(message="hi")
        assert result["status"] == "SUCCESS" and result["method"] == "terminal-bell"


class TestWebReadExtraction:
    def test_body_wrapper_classes_never_hide_the_page(self, fake_requests):
        """Regression: Wikipedia's <body> has classes like 'vector-toc-available'/'...-sidebar...'."""
        from ai.modules.tools_web.tools import web_read
        html = ('<html><body class="skin-vector vector-toc-available has-sidebar">'
                '<div class="mw-sidebar">Navigation links</div>'
                '<div id="content"><h1>Asynchronous I/O</h1><p>' + "Real article text. " * 20 + '</p></div></body></html>')
        fake_requests.get.return_value = FakeResponse(html)
        content = web_read(url="https://wiki.example/a")["content"]
        assert "Real article text." in content and "# Asynchronous I/O" in content
        assert "Navigation links" not in content

    def test_prefers_main_content_and_drops_chrome(self, fake_requests):
        from ai.modules.tools_web.tools import web_read
        html = ('<html><body><div class="sphinxsidebar" role="navigation"><p>Previous topic</p></div>'
                '<header><p>Site header</p></header>'
                '<div class="body" role="main"><h1>Doc</h1><p>' + "Useful docs. " * 30 + '<p>unclosed para<li>stray item</div>'
                '<footer>Copyright</footer></body></html>')
        fake_requests.get.return_value = FakeResponse(html)
        content = web_read(url="https://docs.example/x")["content"]
        assert content.startswith("# Doc") and "Useful docs." in content and "stray item" in content
        for chrome in ("Previous topic", "Site header", "Copyright"):
            assert chrome not in content

    def test_charset_from_meta_when_header_has_none(self, fake_requests):
        """Regression: requests assumes ISO-8859-1 for text/html without charset (mojibake)."""
        from ai.modules.tools_web.tools import web_read
        resp = FakeResponse('<html><head><meta charset="utf-8"><title>asyncio — I/O</title></head><body><p>ação</p></body></html>',
                            content_type="text/html")
        fake_requests.get.return_value = resp
        result = web_read(url="https://e.com")
        assert result["title"] == "asyncio — I/O" and "ação" in result["content"]

    def test_blocked_site_hint(self, fake_requests):
        from ai.modules.tools_web.tools import web_read
        fake_requests.get.return_value = FakeResponse("denied", status=403)
        assert "browser tool" in web_read(url="https://e.com")["error"]


class TestDocstringsAreAgentFacing:
    """The agent only sees a tool's docstring (ToolRegistry.get_tool_info): keep it usable."""

    NEW_TOOLS = ["read_files", "delete_file", "grep_file", "web_search", "web_read", "send_notification"]

    @pytest.fixture
    def tools(self):
        import ai.tools.agent_tools as agent_tools
        return agent_tools.AVAILABLE_TOOLS

    @pytest.mark.parametrize("name", sorted(ALL_TOOLS))
    def test_tool_docs_follow_agent_conventions(self, tools, name):
        import inspect
        from ai.tools.tool_registry import ToolRegistry
        doc = inspect.cleandoc(tools[name].__doc__)
        assert "YAML" not in doc, f"{name}: the agent writes XML; YAML instructions conflict"
        assert "Args:" in doc and "Returns:" in doc
        # Python type annotations mean nothing to a model writing XML
        for python_ism in ("Dict[", "List[", "Optional[", "Any]", "kwargs", "(str)", "(str ", "(bool)"):
            assert python_ism not in doc, f"{name}: '{python_ism}' in docstring"
        schema = ToolRegistry.parse_docstring_to_schema(name, tools[name])["parameters"]
        documented = set(schema["properties"]) - {"intent"}
        assert documented, f"{name}: no parseable 'name (type): description' Args lines"
        for param in documented:
            assert param in inspect.getsource(tools[name]), f"{name}: documents '{param}' but never reads it"

    def test_tool_info_is_dedented(self, tools):
        from ai.tools.tool_registry import ToolRegistry
        registry = ToolRegistry()
        registry.register_tool("grep_file", tools["grep_file"])
        info = registry.get_tool_info("grep_file").splitlines()
        assert info[0] == "- grep_file:"
        assert info[1].startswith("  Find lines") and any(l == "  Args:" for l in info)


    def test_memory_tool_docs_are_parseable(self):
        from ai.modules.vector_memory.memory_tools import MemoryTools
        from ai.tools.tool_registry import ToolRegistry
        tools = MemoryTools(None).get_tools()
        schema = ToolRegistry.parse_docstring_to_schema("query_memory", tools["query_memory"])["parameters"]
        assert {"query", "top_k"} <= set(schema["properties"])
        assert "top_k" not in schema["required"] and "query" in schema["required"]

    def test_content_params_ask_for_cdata(self, tools):
        for name, params in (("write_file", ["content"]), ("patch_file", ["search", "replace"])):
            doc = tools[name].__doc__
            assert "CDATA" in doc, name
