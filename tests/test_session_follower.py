import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from session_follower import SessionFollower


def make_status_dir(tmp_path: Path) -> Path:
    status = tmp_path / "status"
    status.mkdir(parents=True)
    return status


def write_json(path: Path, data: dict[str, str]) -> None:
    path.write_text(json.dumps(data), encoding="utf-8")


def read_json(path: Path) -> dict[str, str]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_follow_replaces_matching_chat_and_clears_entry(tmp_path: Path) -> None:
    status = make_status_dir(tmp_path)
    write_json(status / "session_ids.json", {"main": "old-1", "Workbench": "keep-1"})
    follower = SessionFollower(status)
    follower.remember_cleared("main", "old-1")
    assert follower.follow_new("main", "new-1") is True
    assert read_json(status / "session_ids.json") == {
        "main": "new-1", "Workbench": "keep-1"}
    assert read_json(status / "cleared_sessions.json") == {}


def test_follow_with_nothing_remembered_returns_false(tmp_path: Path) -> None:
    status = make_status_dir(tmp_path)
    write_json(status / "session_ids.json", {"main": "old-1"})
    assert SessionFollower(status).follow_new("main", "new-1") is False
    assert read_json(status / "session_ids.json") == {"main": "old-1"}


def test_old_id_matching_no_chat_returns_false(tmp_path: Path) -> None:
    status = make_status_dir(tmp_path)
    write_json(status / "session_ids.json", {"main": "other-1"})
    follower = SessionFollower(status)
    follower.remember_cleared("main", "old-1")
    assert follower.follow_new("main", "new-1") is False
    assert read_json(status / "session_ids.json") == {"main": "other-1"}


def test_corrupt_session_ids_returns_false_without_raising(tmp_path: Path) -> None:
    status = make_status_dir(tmp_path)
    (status / "session_ids.json").write_text("{not json", encoding="utf-8")
    follower = SessionFollower(status)
    follower.remember_cleared("main", "old-1")
    assert follower.follow_new("main", "new-1") is False


def test_follow_keeps_the_other_surfaces_entry(tmp_path: Path) -> None:
    status = make_status_dir(tmp_path)
    write_json(status / "session_ids.json", {"main": "old-1", "Workbench": "old-2"})
    follower = SessionFollower(status)
    follower.remember_cleared("main", "old-1")
    follower.remember_cleared("Workbench", "old-2")
    assert follower.follow_new("main", "new-1") is True
    assert read_json(status / "cleared_sessions.json") == {"Workbench": "old-2"}


def test_empty_new_id_returns_false_and_changes_nothing(tmp_path: Path) -> None:
    status = make_status_dir(tmp_path)
    write_json(status / "session_ids.json", {"main": "old-1"})
    follower = SessionFollower(status)
    follower.remember_cleared("main", "old-1")
    assert follower.follow_new("main", "") is False
    assert read_json(status / "session_ids.json") == {"main": "old-1"}
    assert read_json(status / "cleared_sessions.json") == {"main": "old-1"}


def test_remember_ignores_an_empty_old_id(tmp_path: Path) -> None:
    status = make_status_dir(tmp_path)
    SessionFollower(status).remember_cleared("main", "")
    assert not (status / "cleared_sessions.json").exists()


def test_writes_leave_no_temp_files(tmp_path: Path) -> None:
    status = make_status_dir(tmp_path)
    follower = SessionFollower(status)
    follower.remember_cleared("main", "old-1")
    follower.follow_new("main", "new-1")
    assert list(status.glob("*.tmp")) == []
