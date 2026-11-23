import io
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import activity_hook
from activity_hook import ActivityRecorder
from tool_activity import ToolActivity, ToolEventClassifier

NOW = "2026-11-08T12:00:00"
SURFACE = "surf-1"


def classify(payload: dict) -> ToolActivity | None:
    return ToolEventClassifier().classify(payload)


def make_root(tmp_path: Path) -> Path:
    status = tmp_path / "repo" / "status"
    status.mkdir(parents=True)
    lines = ['name = "repo"', f'wmux_surface = "{SURFACE}"', 'task = "refactor"']
    (status / "a.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return tmp_path


def read_status(root: Path) -> str:
    return (root / "repo" / "status" / "a.toml").read_text(encoding="utf-8")


def test_bash_command_becomes_last_tool() -> None:
    payload = {"hook_event_name": "PreToolUse", "tool_name": "Bash",
               "tool_input": {"command": "git status"}}
    activity = classify(payload)
    assert activity is not None
    assert activity.last_tool == "Bash git status"
    assert activity.state == "working"


def test_bash_session_send_gives_worker() -> None:
    payload = {"hook_event_name": "PreToolUse", "tool_name": "Bash",
               "tool_input": {"command": "pwsh session.ps1 send hello"}}
    activity = classify(payload)
    assert activity is not None
    assert activity.state == "worker"


def test_agent_tool_gives_worker() -> None:
    payload = {"hook_event_name": "PreToolUse", "tool_name": "Agent", "tool_input": {}}
    activity = classify(payload)
    assert activity is not None
    assert activity.state == "worker"


def test_notification_gives_needs_you() -> None:
    payload = {"hook_event_name": "Notification", "message": "Claude needs your input"}
    activity = classify(payload)
    assert activity is not None
    assert activity.state == "needs-you"
    assert activity.last_tool == "Claude needs your input"


def test_read_tool_uses_file_path() -> None:
    payload = {"hook_event_name": "PreToolUse", "tool_name": "Read",
               "tool_input": {"file_path": "src/main.py", "description": "ignored"}}
    activity = classify(payload)
    assert activity is not None
    assert activity.last_tool == "Read src/main.py"


def test_quotes_and_backslashes_are_removed() -> None:
    payload = {"hook_event_name": "PreToolUse", "tool_name": "Bash",
               "tool_input": {"command": 'echo "a\\b\nnext"'}}
    activity = classify(payload)
    assert activity is not None
    assert '"' not in activity.last_tool
    assert "\\" not in activity.last_tool
    assert "\n" not in activity.last_tool


def test_unknown_event_returns_none() -> None:
    assert classify({"hook_event_name": "PostToolUse"}) is None


def test_update_writes_last_tool_lines(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    ActivityRecorder().update(root, SURFACE, "working", NOW, "Bash git status")
    text = read_status(root)
    assert 'last_tool = "Bash git status"' in text
    assert f'last_tool_at = "{NOW}"' in text


def test_idle_removes_last_tool_lines(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    recorder = ActivityRecorder()
    recorder.update(root, SURFACE, "working", NOW, "Bash git status")
    recorder.update(root, SURFACE, "idle", "2026-11-08T13:00:00")
    text = read_status(root)
    assert "last_tool" not in text
    assert "last_tool_at" not in text


def test_main_pretooluse_updates_status_file(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = make_root(tmp_path)
    payload = {"hook_event_name": "PreToolUse", "tool_name": "Bash",
               "tool_input": {"command": "git status"}}
    fake_hook = tmp_path / "fake" / "scripts" / "activity_hook.py"
    monkeypatch.setattr(activity_hook, "Path", lambda _: fake_hook)
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(payload)))
    monkeypatch.setenv("WMUX_SURFACE_ID", SURFACE)
    assert activity_hook.main() == 0
    text = read_status(root)
    assert 'activity = "working"' in text
    assert 'last_tool = "Bash git status"' in text


def test_edit_tool_sets_edited_file_to_base_name_forward_slash() -> None:
    payload = {"hook_event_name": "PreToolUse", "tool_name": "Edit",
               "tool_input": {"file_path": "src/cards/main.py"}}
    activity = classify(payload)
    assert activity is not None
    assert activity.edited_file == "main.py"


def test_write_tool_sets_edited_file_to_base_name_backslash() -> None:
    payload = {"hook_event_name": "PreToolUse", "tool_name": "Write",
               "tool_input": {"file_path": "E:\\repos\\mods\\card.py"}}
    activity = classify(payload)
    assert activity is not None
    assert activity.edited_file == "card.py"


def test_notebook_edit_uses_notebook_path() -> None:
    payload = {"hook_event_name": "PreToolUse", "tool_name": "NotebookEdit",
               "tool_input": {"notebook_path": "notebooks/analysis.ipynb"}}
    activity = classify(payload)
    assert activity is not None
    assert activity.edited_file == "analysis.ipynb"


def test_read_tool_leaves_edited_file_empty() -> None:
    payload = {"hook_event_name": "PreToolUse", "tool_name": "Read",
               "tool_input": {"file_path": "src/cards/main.py"}}
    activity = classify(payload)
    assert activity is not None
    assert activity.edited_file == ""
