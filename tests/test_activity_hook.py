import io
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import activity_hook
from activity_hook import ActivityRecorder

NOW = "2026-11-08T12:00:00"
SURFACE = "surf-1"


def make_root(tmp_path: Path) -> Path:
    workspaces = tmp_path / "repo" / "status" / "workspaces"
    workspaces.mkdir(parents=True)
    lines = ['name = "repo"', f'wmux_surface = "{SURFACE}"', 'task = "refactor"']
    (tmp_path / "repo" / "status" / "a.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")
    other = ['name = "other"', 'wmux_surface = "surf-2"']
    (workspaces / "b.toml").write_text("\n".join(other) + "\n", encoding="utf-8")
    return tmp_path


def read(root: Path, name: str) -> str:
    return (root / "repo" / "status" / name).read_text(encoding="utf-8")


def test_working_writes_both_keys_in_matching_file_only(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    ActivityRecorder().update(root, SURFACE, "working", NOW)
    text = read(root, "a.toml")
    assert 'activity = "working"' in text
    assert f'activity_at = "{NOW}"' in text
    assert read(root, "workspaces/b.toml") == 'name = "other"\nwmux_surface = "surf-2"\n'


def test_idle_removes_task_line(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    ActivityRecorder().update(root, SURFACE, "idle", NOW)
    text = read(root, "a.toml")
    assert 'task = "refactor"' not in text
    assert 'activity = "idle"' in text


def test_existing_lines_stay(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    ActivityRecorder().update(root, SURFACE, "working", NOW)
    text = read(root, "a.toml")
    assert 'name = "repo"' in text
    assert f'wmux_surface = "{SURFACE}"' in text


def test_second_call_replaces_not_duplicates(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    recorder = ActivityRecorder()
    recorder.update(root, SURFACE, "working", NOW)
    recorder.update(root, SURFACE, "idle", "2026-11-08T13:00:00")
    text = read(root, "a.toml")
    assert text.count("activity =") == 1
    assert text.count("activity_at =") == 1
    assert 'activity = "idle"' in text
    assert 'activity_at = "2026-11-08T13:00:00"' in text


def test_non_matching_surface_changes_nothing(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    before = read(root, "a.toml")
    ActivityRecorder().update(root, "surf-9", "working", NOW)
    assert read(root, "a.toml") == before


def test_crlf_newline_style_is_kept(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    path = root / "repo" / "status" / "a.toml"
    path.write_bytes(path.read_text(encoding="utf-8").replace("\n", "\r\n").encode("utf-8"))
    ActivityRecorder().update(root, SURFACE, "working", NOW)
    assert b"\r\n" in path.read_bytes()
    assert path.read_bytes().count(b"\n") == path.read_bytes().count(b"\r\n")


def test_update_leaves_no_temp_files(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    ActivityRecorder().update(root, SURFACE, "working", NOW)
    assert list((root / "repo" / "status").glob("*.tmp")) == []


def test_new_keys_go_before_the_first_table(tmp_path: Path) -> None:
    status = tmp_path / "repo" / "status"
    status.mkdir(parents=True)
    path = status / "a.toml"
    path.write_text('wmux_surface = "s1"\n[workers.x]\nstate = "ok"\n', encoding="utf-8")
    ActivityRecorder().update(tmp_path, "s1", "working", "2026-11-08T12:00:00+00:00")
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines.index('activity = "working"') < lines.index("[workers.x]")


def _raise_update(self: object, root: Path, surface_id: str, state: str, now: str,
                  prompt_started: bool = False) -> None:
    raise RuntimeError("hook blew up")


def test_main_logs_errors_and_returns_zero(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    log = tmp_path / "hook-errors.log"
    monkeypatch.setattr(activity_hook, "ERROR_LOG", log)
    monkeypatch.setattr(activity_hook.ActivityRecorder, "update", _raise_update)
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"hook_event_name": "Stop"})))
    monkeypatch.setenv("WMUX_SURFACE_ID", SURFACE)
    assert activity_hook.main() == 0
    assert "RuntimeError: hook blew up" in log.read_text(encoding="utf-8")


def test_main_swallows_errors_when_log_is_unwritable(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(activity_hook, "ERROR_LOG", tmp_path / "missing-dir" / "log")
    monkeypatch.setattr(activity_hook.ActivityRecorder, "update", _raise_update)
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"hook_event_name": "Stop"})))
    monkeypatch.setenv("WMUX_SURFACE_ID", SURFACE)
    assert activity_hook.main() == 0


def test_tool_calls_counts_1_2_3_over_three_tool_events(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    recorder = ActivityRecorder()
    for expected in (1, 2, 3):
        recorder.update(root, SURFACE, "working", NOW, "Bash git status")
        assert f"tool_calls = {expected}" in read(root, "a.toml")


def test_prompt_event_resets_tool_calls_to_zero(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    recorder = ActivityRecorder()
    recorder.update(root, SURFACE, "working", NOW, "Bash git status")
    recorder.update(root, SURFACE, "working", NOW)
    assert "tool_calls = 0" in read(root, "a.toml")


def test_edited_file_writes_last_file_line(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    ActivityRecorder().update(root, SURFACE, "working", NOW, "Edit main.py", "main.py")
    assert 'last_file = "main.py"' in read(root, "a.toml")


def test_no_edited_file_writes_no_last_file_line(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    ActivityRecorder().update(root, SURFACE, "working", NOW, "Bash git status")
    assert "last_file" not in read(root, "a.toml")


def test_idle_removes_last_file_and_tool_calls(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    recorder = ActivityRecorder()
    recorder.update(root, SURFACE, "working", NOW, "Edit main.py", "main.py")
    recorder.update(root, SURFACE, "idle", "2026-11-08T13:00:00")
    text = read(root, "a.toml")
    assert "last_file" not in text
    assert "tool_calls" not in text


def test_chat_session_skips_every_hook_effect(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(activity_hook, "handle_stop", lambda *args: calls.append("stop"))
    monkeypatch.setattr(activity_hook.ActivityRecorder, "update", lambda *args, **kwargs: calls.append("update"))
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps({"hook_event_name": "Stop"})))
    monkeypatch.setenv("WMUX_SURFACE_ID", SURFACE)
    monkeypatch.setenv(activity_hook.CHAT_SESSION_ENV, "1")
    assert activity_hook.main() == 0
    assert calls == []


def test_chat_session_marker_matches_the_sdk_factory() -> None:
    from workbench.sdk_client_factory import CHAT_SESSION_ENV
    assert activity_hook.CHAT_SESSION_ENV == CHAT_SESSION_ENV


def make_phase_root(tmp_path: Path) -> Path:
    root = make_root(tmp_path)
    path = root / "repo" / "status" / "a.toml"
    text = path.read_text(encoding="utf-8")
    path.write_text(text + 'phase = "finished"\n', encoding="utf-8")
    return root


def test_prompt_started_removes_phase_line(tmp_path: Path) -> None:
    root = make_phase_root(tmp_path)
    ActivityRecorder().update(root, SURFACE, "working", NOW, prompt_started=True)
    assert "phase" not in read(root, "a.toml")


def test_without_prompt_started_the_phase_line_stays(tmp_path: Path) -> None:
    root = make_phase_root(tmp_path)
    ActivityRecorder().update(root, SURFACE, "working", NOW)
    assert 'phase = "finished"' in read(root, "a.toml")
