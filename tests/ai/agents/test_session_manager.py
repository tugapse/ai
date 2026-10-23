import hashlib
import json
import os
import shutil
import uuid

from ai.agents.session_manager import AgentSessionManager


def _reset_storage_for_directory(working_directory: str):
    digest = hashlib.sha256(os.path.abspath(working_directory).encode("utf-8")).hexdigest()[:16]
    storage_dir = os.path.join("logs", "agents", digest)
    os.makedirs(storage_dir, exist_ok=True)
    for filename in os.listdir(storage_dir):
        file_path = os.path.join(storage_dir, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
    return storage_dir


def test_session_manager_uses_hashed_working_directory_for_unique_storage(tmp_path):
    working_directory = str(tmp_path / "project-root")
    manager = AgentSessionManager("session-123", working_directory=working_directory)

    digest = hashlib.sha256(os.path.abspath(working_directory).encode("utf-8")).hexdigest()[:16]

    assert manager.parent_dir == digest
    assert manager.storage_dir == os.path.join("logs", "agents", digest)
    assert os.path.isdir(manager.storage_dir)
    assert manager.session_path == os.path.join(manager.storage_dir, "session-123.json")


def test_commit_and_get_session_round_trip():
    working_directory = os.getcwd()
    _reset_storage_for_directory(working_directory)
    manager = AgentSessionManager("session-commit", working_directory=working_directory)
    state = {"current_agent": "MANAGER", "iteration": 3, "memory": {"notes": "ok"}}

    manager.commit(state)
    hydrated = manager.get_session()

    assert hydrated == state
    assert os.path.exists(manager.session_path)


def test_get_session_handles_compressed_payloads():
    working_directory = os.getcwd()
    _reset_storage_for_directory(working_directory)
    manager = AgentSessionManager("session-compressed", working_directory=working_directory)
    state = {"current_agent": "CODER", "iteration": 7, "memory": {"notes": "compressed"}}

    manager.commit(state, compress=True)
    hydrated = manager.get_session()

    assert hydrated == state


def test_get_history_summary_returns_turn_metadata():
    working_directory = os.getcwd()
    _reset_storage_for_directory(working_directory)
    manager = AgentSessionManager("session-history", working_directory=working_directory)

    manager.commit({"current_agent": "MANAGER", "iteration": 1})
    manager.commit({"current_agent": "CODER", "iteration": 2})

    summary = manager.get_history_summary()

    assert len(summary) == 2
    assert summary[0]["agent"] == "MANAGER"
    assert summary[0]["iteration"] == 1
    assert summary[1]["agent"] == "CODER"
    assert summary[1]["iteration"] == 2


def test_extract_user_request_from_entry_handles_direct_and_history_messages():
    direct_entry = {"state": {"user_request": "Create a dashboard"}}
    memory_entry = {"state": {"memory": {"MANAGER": {"messages_received": [{"from": "USER", "message": "Fix login"}]}}}}
    history_entry = {"state": {"agents": {"MASTER": {"history": [{"from": "USER", "message": "Refactor API"}]}}}}

    assert AgentSessionManager._extract_user_request_from_entry(direct_entry) == "Create a dashboard"
    assert AgentSessionManager._extract_user_request_from_entry(memory_entry) == "Fix login"
    assert AgentSessionManager._extract_user_request_from_entry(history_entry) == "Refactor API"
    assert AgentSessionManager._extract_user_request_from_entry({"state": {"memory": {}}}) is None


def test_list_sessions_extracts_user_request_from_latest_jsonl_entry():
    working_directory = os.getcwd()
    storage_dir = _reset_storage_for_directory(working_directory)
    session_id = f"session-456-{uuid.uuid4().hex}"
    session_path = os.path.join(storage_dir, f"{session_id}.json")
    payload = {
        "state": {
            "memory": {
                "MANAGER": {
                    "messages_received": [
                        {"from": "USER", "message": "Build a new API endpoint"}
                    ]
                }
            }
        }
    }

    with open(session_path, "w", encoding="utf-8") as session_file:
        session_file.write(json.dumps(payload) + "\n")

    try:
        sessions = AgentSessionManager.list_sessions(working_directory)
        assert sessions == [{
            "session_id": session_id,
            "filename": session_id,
            "user_request": "Build a new API endpoint",
        }]
    finally:
        if os.path.exists(session_path):
            os.remove(session_path)
        if os.path.isdir(storage_dir) and not os.listdir(storage_dir):
            shutil.rmtree(storage_dir)


def test_list_sessions_returns_empty_list_when_storage_missing():
    working_directory = os.getcwd()
    digest = hashlib.sha256(os.path.abspath(working_directory).encode("utf-8")).hexdigest()[:16]
    storage_dir = os.path.join("logs", "agents", digest)
    if os.path.isdir(storage_dir):
        for filename in os.listdir(storage_dir):
            os.remove(os.path.join(storage_dir, filename))
        os.rmdir(storage_dir)

    assert AgentSessionManager.list_sessions(working_directory) == []
