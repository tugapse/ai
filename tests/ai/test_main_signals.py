"""Exit codes after a graceful shutdown on a signal (main.signal_exit_code)."""

import signal

import pytest

from ai.main import signal_exit_code


@pytest.mark.parametrize("signum, code", [(signal.SIGINT, 130), (signal.SIGTERM, 143)])
def test_an_interrupted_command_exits_128_plus_the_signal(signum, code):
    assert signal_exit_code(signum) == code


@pytest.mark.parametrize("signum", [signal.SIGINT, signal.SIGTERM])
def test_a_server_stop_is_a_normal_end(signum):
    assert signal_exit_code(signum, serving=True) == 0
