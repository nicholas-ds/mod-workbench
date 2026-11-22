"""Tests for ClaudeEventTranslator (Task T1a): one test per mapping row."""

from workbench.claude_translator import ClaudeEventTranslator
from workbench.agent_event import (
    CLAUDE_SOURCE,
    STATE_ERROR,
    STATE_FINISHED,
    STATE_IDLE,
    STATE_NEEDS_YOU,
    STATE_RUNNING,
)


def _translate(payload: dict, now_ms: int = 1000):
    return ClaudeEventTranslator().translate(payload, now_ms)


def _base_payload(event_name: str) -> dict:
    return {"hook_event_name": event_name, "session_id": "s1", "cwd": "E:/repo"}


def test_user_prompt_submit_is_running():
    event = _translate(_base_payload("UserPromptSubmit"))
    assert event.state == STATE_RUNNING
    assert event.agent_id == "s1"


def test_pre_tool_use_is_running_and_counts_tool():
    payload = _base_payload("PreToolUse") | {
        "tool_name": "Bash", "tool_input": {"command": "git status"},
    }
    event = _translate(payload)
    assert event.state == STATE_RUNNING
    assert event.counts_tool is True
    assert event.last_tool == "Bash git status"


def test_pre_tool_use_detail_is_one_line_and_cut_to_100_chars():
    payload = _base_payload("PreToolUse") | {
        "tool_name": "Bash", "tool_input": {"command": "a\n b  c " + "x" * 120},
    }
    event = _translate(payload)
    assert "\n" not in event.last_tool
    assert len(event.last_tool.split(" ", 1)[1]) <= 100


def test_pre_tool_use_picks_first_non_empty_detail_key():
    payload = _base_payload("PreToolUse") | {
        "tool_name": "Grep", "tool_input": {"pattern": "todo", "command": ""},
    }
    event = _translate(payload)
    assert event.last_tool == "Grep todo"


def test_pre_tool_use_edit_sets_last_file_with_forward_slashes():
    payload = _base_payload("PreToolUse") | {
        "tool_name": "Edit", "tool_input": {"file_path": "E:/repos/mods/main.py"},
    }
    event = _translate(payload)
    assert event.last_file == "main.py"


def test_pre_tool_use_write_sets_last_file_with_backslashes():
    payload = _base_payload("PreToolUse") | {
        "tool_name": "Write", "tool_input": {"file_path": "E:\\repos\\mods\\main.py"},
    }
    event = _translate(payload)
    assert event.last_file == "main.py"


def test_pre_tool_use_notebook_edit_uses_notebook_path():
    payload = _base_payload("PreToolUse") | {
        "tool_name": "NotebookEdit", "tool_input": {"notebook_path": "/tmp/nb.ipynb"},
    }
    event = _translate(payload)
    assert event.last_file == "nb.ipynb"


def test_permission_request_needs_you_with_tool_name():
    payload = _base_payload("PermissionRequest") | {"tool_name": "Bash"}
    event = _translate(payload)
    assert event.state == STATE_NEEDS_YOU
    assert event.last_tool == "Bash"
    assert event.counts_tool is False


def test_subagent_start_uses_agent_id_parent_and_title():
    payload = _base_payload("SubagentStart") | {
        "agent_id": "a9", "agent_type": "explore",
    }
    event = _translate(payload)
    assert event.state == STATE_RUNNING
    assert event.agent_id == "a9"
    assert event.parent_id == "s1"
    assert event.title == "explore"


def test_subagent_start_without_agent_id_is_none():
    assert _translate(_base_payload("SubagentStart")) is None


def test_subagent_stop_is_finished():
    payload = _base_payload("SubagentStop") | {"agent_id": "a9"}
    event = _translate(payload)
    assert event.state == STATE_FINISHED
    assert event.agent_id == "a9"


def test_stop_is_idle():
    assert _translate(_base_payload("Stop")).state == STATE_IDLE


def test_stop_failure_is_error():
    assert _translate(_base_payload("StopFailure")).state == STATE_ERROR


def test_session_end_is_finished():
    assert _translate(_base_payload("SessionEnd")).state == STATE_FINISHED


def test_missing_session_id_is_none():
    payload = {"hook_event_name": "Stop"}
    assert _translate(payload) is None


def test_unknown_event_is_none():
    assert _translate(_base_payload("Nonsense")) is None


def test_cwd_and_source_and_time_are_copied():
    event = _translate(_base_payload("Stop"), now_ms=42)
    assert event.cwd == "E:/repo"
    assert event.source == CLAUDE_SOURCE
    assert event.at_ms == 42
