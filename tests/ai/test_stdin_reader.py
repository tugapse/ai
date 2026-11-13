"""read_piped_stdin: reads piped input without hanging on a stdin pipe nobody writes to."""

import os
import threading
import time

import pytest


from ai.stdin_reader import read_piped_stdin


@pytest.fixture
def pipe():
    """(reader stream, writer fd); both closed at the end."""
    read_fd, write_fd = os.pipe()
    reader = os.fdopen(read_fd, "r")
    state = {"write_fd": write_fd}
    yield reader, state
    reader.close()
    if state["write_fd"] is not None:
        os.close(state["write_fd"])


def close_writer(state):
    os.close(state["write_fd"])
    state["write_fd"] = None


def test_piped_data_is_read_with_a_prompt(pipe):
    reader, state = pipe
    os.write(state["write_fd"], b"  diff --git a/x b/x\n")
    close_writer(state)
    assert read_piped_stdin(True, stream=reader, wait=1) == "diff --git a/x b/x"


def test_open_pipe_without_data_is_ignored_when_a_prompt_was_given(pipe):
    """The bug: an inherited stdin pipe that never closes hung `ai -m` forever."""
    reader, _ = pipe
    start = time.monotonic()
    assert read_piped_stdin(True, stream=reader, wait=0.2) == ""
    assert time.monotonic() - start < 2


def test_data_arriving_within_the_wait_is_read_to_eof(pipe):
    reader, state = pipe

    def producer():
        time.sleep(0.1)
        os.write(state["write_fd"], b"part 1 ")
        time.sleep(0.3)  # later chunks may take longer than the wait: still read to EOF
        os.write(state["write_fd"], b"part 2")
        close_writer(state)

    threading.Thread(target=producer).start()
    assert read_piped_stdin(True, stream=reader, wait=0.2) == "part 1 part 2"


def test_without_a_prompt_stdin_is_awaited(pipe, monkeypatch):
    """When stdin is the only input, a slow producer is waited for (with a hint)."""
    import ai.stdin_reader as cli_args
    monkeypatch.setattr(cli_args, "STDIN_HINT_AFTER", 0.05)
    hints = []
    monkeypatch.setattr(cli_args.func, "out", lambda msg, *a, **k: hints.append(msg))
    reader, state = pipe

    def producer():
        time.sleep(0.3)
        os.write(state["write_fd"], b"late input")
        close_writer(state)

    threading.Thread(target=producer).start()
    assert read_piped_stdin(False, stream=reader) == "late input"
    assert any("Waiting for input on stdin" in h for h in hints)


def test_env_var_sets_the_wait(pipe, monkeypatch):
    monkeypatch.setenv("AI_STDIN_WAIT", "0.1")
    reader, _ = pipe
    start = time.monotonic()
    assert read_piped_stdin(True, stream=reader) == ""
    assert time.monotonic() - start < 1


def test_regular_file_is_read(tmp_path):
    path = tmp_path / "input.txt"
    path.write_text("from a file\n")
    with open(path) as stream:
        assert read_piped_stdin(True, stream=stream, wait=0) == "from a file"


def test_dev_null_is_empty():
    with open(os.devnull) as stream:
        assert read_piped_stdin(True, stream=stream) == ""


def test_closed_or_missing_stream_is_empty(pipe):
    reader, _ = pipe
    reader.close()
    assert read_piped_stdin(True, stream=reader) == ""
