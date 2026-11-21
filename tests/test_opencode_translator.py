"""Tests for OpencodeEventTranslator (Task T1a): one test per mapping row."""

from workbench.opencode_translator import OpencodeEventTranslator
from workbench.agent_event import (
    OPENCODE_SOURCE,
    STATE_ERROR,
    STATE_IDLE,
    STATE_RUNNING,
)


def _translate(payload: dict, now_ms: int = 1000):
    return OpencodeEventTranslator().translate(payload, now_ms)


def _base_payload(event_type: str) -> dict:
    return {"type": event_type, "session_id": "ses-1", "directory": "E:/repo"}


def test_session_status_busy_is_running():
    payload = _base_payload("session.status") | {"status": "busy"}
    assert _translate(payload).state == STATE_RUNNING


def test_session_status_retry_is_running():
    payload = _base_payload("session.status") | {"status": "retry"}
    assert _translate(payload).state == STATE_RUNNING


def test_session_status_idle_is_idle():
    payload = _base_payload("session.status") | {"status": "idle"}
    assert _translate(payload).state == STATE_IDLE


def test_session_status_unknown_status_is_none():
    payload = _base_payload("session.status") | {"status": "weird"}
    assert _translate(payload) is None


def test_session_idle_is_idle():
    assert _translate(_base_payload("session.idle")).state == STATE_IDLE


def test_session_error_is_error():
    assert _translate(_base_payload("session.error")).state == STATE_ERROR


def test_tool_execute_after_is_running_and_counts_tool():
    payload = _base_payload("tool.execute.after") | {
        "tool": "edit", "file": "E:/repo/src/main.py",
    }
    event = _translate(payload)
    assert event.state == STATE_RUNNING
    assert event.counts_tool is True
    assert event.last_tool == "edit"
    assert event.last_file == "main.py"


def test_tool_execute_after_cuts_tool_to_60_chars():
    payload = _base_payload("tool.execute.after") | {"tool": "t" * 80, "file": ""}
    assert len(_translate(payload).last_tool) == 60


def test_tool_execute_after_file_with_backslashes():
    payload = _base_payload("tool.execute.after") | {
        "tool": "read", "file": "E:\\repo\\src\\main.py",
    }
    assert _translate(payload).last_file == "main.py"


def test_todo_updated_carries_progress():
    payload = _base_payload("todo.updated") | {"progress": "2 of 5 done"}
    event = _translate(payload)
    assert event.state == STATE_RUNNING
    assert event.progress == "2 of 5 done"


def test_missing_session_id_is_none():
    assert _translate({"type": "session.idle"}) is None


def test_unknown_type_is_none():
    assert _translate(_base_payload("session.nonsense")) is None


def test_title_parent_id_cwd_source_and_time_are_copied():
    payload = _base_payload("session.idle") | {
        "title": "Fix bug", "parent_id": "ses-0",
    }
    event = _translate(payload, now_ms=42)
    assert event.agent_id == "ses-1"
    assert event.title == "Fix bug"
    assert event.parent_id == "ses-0"
    assert event.cwd == "E:/repo"
    assert event.source == OPENCODE_SOURCE
    assert event.at_ms == 42


def test_session_done_maps_to_finished() -> None:
    event = OpencodeEventTranslator().translate({"type": "session.done", "session_id": "ses_1"}, 5)
    assert event is not None and event.state == "finished"
