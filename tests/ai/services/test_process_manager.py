import os
import subprocess
import sys

import pytest

from ai.services.process_manager import ProcessManager


class DummyDirectoryManager:
    def __init__(self, tmp_path):
        self.tmp_path = tmp_path

    def get_pid_directory(self):
        return str(self.tmp_path / "pids")


def setup_function():
    ProcessManager._state = {}
    ProcessManager._instance = None


def test_process_manager_uses_exclusive_lock(tmp_path):
    """Only one process instance should be able to acquire the PID lock for a given process."""
    manager_one = ProcessManager(DummyDirectoryManager(tmp_path))
    manager_two = ProcessManager(DummyDirectoryManager(tmp_path))

    manager_one.start()

    with pytest.raises(RuntimeError, match="already running"):
        manager_two.start()

    manager_one.shutdown()
    manager_two.start()
    manager_two.shutdown()


def test_write_overwrites_existing_pid_contents(tmp_path):
    """The writer should replace the current file contents instead of leaving stale content behind."""
    manager = ProcessManager(DummyDirectoryManager(tmp_path))
    manager.start()

    manager.write("abc")
    manager.write("z")

    pid_path = tmp_path / "pids" / f"{manager.process_id}.pid"
    assert pid_path.read_text() == "z"

    manager.shutdown()


def test_write_raises_when_lock_is_not_active(tmp_path):
    """Writing without an active lock should fail loudly so bad state is not silently ignored."""
    manager = ProcessManager(DummyDirectoryManager(tmp_path))

    with pytest.raises(RuntimeError, match="Process lock is not active"):
        manager.write("123")


def test_set_state_writes_plain_text_status(tmp_path):
    """State is saved as aligned key: value lines and always reflects the newest values."""
    manager = ProcessManager(DummyDirectoryManager(tmp_path))
    ProcessManager.set_state("mode", "agent")
    manager.start()

    ProcessManager.set_state("model", "gemma4")
    ProcessManager.set_state("activity", "[3/20] coder: fix parser: step 2")

    text = (tmp_path / "pids" / f"{manager.process_id}.pid").read_text()
    state = ProcessManager.parse(text)
    assert state["pid"] == str(manager.process_id)
    assert state["mode"] == "agent"
    assert state["model"] == "gemma4"
    assert state["activity"] == "[3/20] coder: fix parser: step 2"
    assert "install" in state and "started" in state
    assert text.splitlines()[0].startswith("pid:")

    manager.shutdown()


def test_set_state_rejects_unknown_fields():
    """Only the registry fields are accepted, so the file cannot grow into a memory dump again."""
    with pytest.raises(ValueError, match="Unknown process state field"):
        ProcessManager.set_state("agent_payload", {"big": "thing"})


def test_values_are_single_line_and_bounded():
    """Newlines are collapsed and long values are truncated, so a value never breaks the format."""
    ProcessManager.set_state("activity", "line one\nline two\n\tthree")
    assert ProcessManager._state["activity"] == "line one line two three"

    ProcessManager.set_state("activity", "x" * 500)
    assert len(ProcessManager._state["activity"]) == ProcessManager.MAX_VALUE_LENGTH


def test_list_instances_includes_live_and_removes_stale(tmp_path):
    """Live (locked) instances are listed; unlocked files of dead processes are deleted."""
    manager = ProcessManager(DummyDirectoryManager(tmp_path))
    ProcessManager.set_state("mode", "server")
    manager.start()

    dead = subprocess.Popen([sys.executable, "-c", "pass"])
    dead.wait()
    stale = tmp_path / "pids" / f"{dead.pid}.pid"
    stale.write_text("pid: 1\nmode: chat\n")
    (tmp_path / "pids" / "notes.txt").write_text("ignored")

    instances = ProcessManager.list_instances(str(tmp_path / "pids"))

    assert [i["pid"] for i in instances] == [str(manager.process_id)]
    assert instances[0]["mode"] == "server"
    assert not stale.exists()

    manager.shutdown()
    assert ProcessManager.list_instances(str(tmp_path / "pids")) == []


def test_list_instances_keeps_unlocked_file_of_live_process(tmp_path):
    """A file whose owner is alive but has not locked it yet (starting up) must not be deleted."""
    pid_dir = tmp_path / "pids"
    pid_dir.mkdir()
    starting = pid_dir / f"{os.getpid()}.pid"
    starting.write_text("")

    instances = ProcessManager.list_instances(str(pid_dir))

    assert starting.exists()
    assert instances == [{"pid": str(os.getpid())}]


def test_list_instances_missing_directory(tmp_path):
    assert ProcessManager.list_instances(str(tmp_path / "nope")) == []
