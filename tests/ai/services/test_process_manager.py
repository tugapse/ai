import json

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


def test_set_state_writes_json_to_pid_file(tmp_path):
    """State updates should serialize to JSON and overwrite the PID file with the newest snapshot."""
    manager = ProcessManager(DummyDirectoryManager(tmp_path))
    manager.start()

    ProcessManager.set_state("name", "worker")
    ProcessManager.set_state("count", 3)

    pid_path = tmp_path / "pids" / f"{manager.process_id}.pid"
    assert json.loads(pid_path.read_text()) == {"name": "worker", "count": 3}

    manager.shutdown()
