"""Tests for SessionIdStore: JSON map of name to session id, atomic save."""

from pathlib import Path

from workbench.chat.session_id_store import SessionIdStore


def test_load_missing_file_returns_empty_string(tmp_path: Path) -> None:
    store = SessionIdStore(tmp_path / "sessions.json")
    assert store.load("main") == ""


def test_none_path_loads_and_saves_as_no_op() -> None:
    store = SessionIdStore(None)
    store.save("main", "abc")
    assert store.load("main") == ""


def test_save_then_load_round_trips(tmp_path: Path) -> None:
    store = SessionIdStore(tmp_path / "sessions.json")
    store.save("main", "abc-123")
    assert store.load("main") == "abc-123"


def test_save_keeps_other_names(tmp_path: Path) -> None:
    path = tmp_path / "sessions.json"
    SessionIdStore(path).save("main", "abc")
    SessionIdStore(path).save("test", "xyz")
    assert SessionIdStore(path).load("main") == "abc"
    assert SessionIdStore(path).load("test") == "xyz"


def test_corrupt_file_loads_as_empty(tmp_path: Path) -> None:
    path = tmp_path / "sessions.json"
    path.write_text("{not json", encoding="utf-8")
    assert SessionIdStore(path).load("main") == ""


def test_save_after_corrupt_file_starts_fresh(tmp_path: Path) -> None:
    path = tmp_path / "sessions.json"
    path.write_text("{not json", encoding="utf-8")
    SessionIdStore(path).save("main", "abc")
    assert SessionIdStore(path).load("main") == "abc"


def test_forget_removes_only_that_name(tmp_path: Path) -> None:
    path = tmp_path / "sessions.json"
    store = SessionIdStore(path)
    store.save("main", "abc")
    store.save("test", "xyz")
    store.forget("main")
    assert store.load("main") == ""
    assert store.load("test") == "xyz"


def test_forget_missing_name_does_not_raise(tmp_path: Path) -> None:
    store = SessionIdStore(tmp_path / "sessions.json")
    store.forget("never-saved")


def test_known_ids_returns_both_chat_ids(tmp_path: Path) -> None:
    path = tmp_path / "sessions.json"
    store = SessionIdStore(path)
    store.save("main", "abc-123")
    store.save("test", "xyz-789")
    assert store.known_ids() == frozenset({"abc-123", "xyz-789"})


def test_known_ids_missing_file_returns_empty(tmp_path: Path) -> None:
    assert SessionIdStore(tmp_path / "sessions.json").known_ids() == frozenset()


def test_known_ids_corrupt_file_returns_empty(tmp_path: Path) -> None:
    path = tmp_path / "sessions.json"
    path.write_text("{not json", encoding="utf-8")
    assert SessionIdStore(path).known_ids() == frozenset()


def test_known_ids_no_path_returns_empty() -> None:
    assert SessionIdStore(None).known_ids() == frozenset()
