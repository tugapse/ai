"""
TOTP codes (RFC 6238) and their use in agent permission answers.
"""

import pytest

from ai.config import ProgramSetting
from ai.modules.server.services import totp as T
from ai.modules.server.services.agent_runs import AgentApiError, AgentRun, AgentRunService


class Clock:
    def __init__(self, now=1_700_000_000.0):
        self.now = now

    def __call__(self):
        return self.now


def test_rfc6238_reference_vector():
    # RFC 6238 appendix B, SHA1 secret "12345678901234567890", T=59s -> 94287082 (8 digits).
    secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
    assert T.code_at(secret, 59 // 30) == "287082"  # the last 6 digits


def test_provisioning_uri_has_the_secret_and_period():
    uri = T.provisioning_uri("ABC")
    assert uri.startswith("otpauth://totp/Jarvis:server?secret=ABC") and "period=30" in uri


class TestGuard:
    @pytest.fixture
    def guard(self, tmp_path):
        clock = Clock()
        g = T.TotpGuard(str(tmp_path / "totp.json"), clock=clock)
        g.clock_ref = clock
        return g

    def test_disabled_until_setup_and_file_is_private(self, guard):
        import os, stat
        assert not guard.enabled
        guard.setup()
        assert guard.enabled and stat.S_IMODE(os.stat(guard.path).st_mode) == 0o600

    def test_current_code_passes_once(self, guard):
        secret = guard.setup()
        code = T.code_at(secret, int(guard.clock_ref.now) // 30)
        assert guard.verify(code) is True
        assert guard.verify(code) is False  # replay

    def test_one_step_drift_is_accepted_two_are_not(self, guard):
        secret = guard.setup()
        step = int(guard.clock_ref.now) // 30
        assert guard.verify(T.code_at(secret, step - 1))
        assert not guard.verify(T.code_at(secret, step - 3))

    @pytest.mark.parametrize("code", ["", "12345", "abcdef", None])
    def test_malformed_codes_fail(self, guard, code):
        guard.setup()
        assert guard.verify(code) is False


class TestPermissionAnswers:
    @pytest.fixture
    def service(self, tmp_path):
        guard = T.TotpGuard(str(tmp_path / "totp.json"), clock=Clock())
        config = {}
        cfg = type("Cfg", (), {"get": lambda self, key, default=None: config.get(key, default)})()
        config[ProgramSetting.SERVER_TOTP_ENABLED] = True
        service = AgentRunService(brain_hub=None, config=cfg, totp=guard)
        service.settings = config
        return service

    def pending(self, service, tool):
        import threading
        run = AgentRun("s", totp_tools=service.totp_tools())
        service.current = run
        waiter = {"event": threading.Event(), "decision": "n", "tool": tool, "needs_totp": run.needs_totp(tool)}
        run.pending["r1"] = waiter
        return run, waiter

    def test_without_setup_no_tool_needs_a_code(self, service):
        assert service.totp_tools() == set()
        run, waiter = self.pending(service, "execute_command")
        service.answer_permission(run.run_id, "r1", "yes")
        assert waiter["decision"] == "y"

    def test_after_setup_default_tools_need_a_code(self, service):
        service.totp.setup()
        assert service.totp_tools() == {"execute_command", "delete_file"}

    def test_off_unless_enabled_in_config_even_with_a_secret(self, service):
        # First release ships with TOTP off: a secret alone does not turn it on.
        service.totp.setup()
        service.settings[ProgramSetting.SERVER_TOTP_ENABLED] = False
        assert service.totp_tools() == set()
        del service.settings[ProgramSetting.SERVER_TOTP_ENABLED]
        assert service.totp_tools() == set()

    def test_missing_and_wrong_code_are_401_and_request_stays_open(self, service):
        service.totp.setup()
        run, waiter = self.pending(service, "execute_command")
        for code in (None, "000000"):
            with pytest.raises(AgentApiError) as e:
                service.answer_permission(run.run_id, "r1", "yes", code)
            assert e.value.status == 401
        assert not waiter["event"].is_set() and "r1" in run.pending

    def test_valid_code_approves_and_always_becomes_yes(self, service):
        secret = service.totp.setup()
        run, waiter = self.pending(service, "execute_command")
        code = T.code_at(secret, int(service.totp.clock()) // 30)
        service.answer_permission(run.run_id, "r1", "always", code)
        assert waiter["decision"] == "y" and waiter["event"].is_set()

    def test_deny_needs_no_code(self, service):
        service.totp.setup()
        run, waiter = self.pending(service, "delete_file")
        service.answer_permission(run.run_id, "r1", "no")
        assert waiter["decision"] == "n"

    def test_other_tools_need_no_code(self, service):
        service.totp.setup()
        run, waiter = self.pending(service, "write_file")
        service.answer_permission(run.run_id, "r1", "always")
        assert waiter["decision"] == "a"
