"""Tests for the chat job store file format."""

from pathlib import Path

from workbench.chat_job import KIND_CLAUDE_AGENT, KIND_GLM_SESSION, STATE_FINISHED, STATE_RUNNING, ChatJob
from workbench.chat_job_store import ChatJobStore


def job(job_id: str, result: str = "") -> ChatJob:
    return ChatJob(
        job_id=job_id,
        kind=KIND_CLAUDE_AGENT,
        chat="chat-a",
        started_by="agent",
        state=STATE_FINISHED if result else STATE_RUNNING,
        result=result,
        started_ms=100,
        updated_ms=100,
    )


def test_round_trip_saves_and_loads_rows(tmp_path: Path) -> None:
    store = ChatJobStore(tmp_path / "jobs")
    jobs = (job("j1"), job("j2", result="ok"))
    store.save("chat-a", jobs)
    loaded = store.load("chat-a")
    assert loaded == jobs
    assert isinstance(loaded, tuple)


def test_missing_file_loads_as_empty_tuple(tmp_path: Path) -> None:
    assert ChatJobStore(tmp_path).load("chat-a") == ()


def test_corrupt_file_loads_as_empty_tuple(tmp_path: Path) -> None:
    path = tmp_path / "chat-a.json"
    path.write_text("{not json", encoding="utf-8")
    assert ChatJobStore(tmp_path).load("chat-a") == ()


def test_rows_with_missing_or_wrong_typed_fields_are_skipped(tmp_path: Path) -> None:
    path = tmp_path / "chat-a.json"
    path.write_text(
        '{"jobs": ['
        '{"job_id": "j1", "kind": "claude_agent", "chat": "chat-a", "started_by": "agent",'
        ' "state": "running", "result": "", "started_ms": 1, "updated_ms": 1},'
        '{"job_id": "j2"},'
        '{"job_id": "j3", "kind": 5, "chat": "chat-a", "started_by": "agent",'
        ' "state": "running", "result": "", "started_ms": 1, "updated_ms": 1},'
        '{"job_id": "j4", "kind": "claude_agent", "chat": "chat-a", "started_by": "agent",'
        ' "state": "running", "result": "", "started_ms": "x", "updated_ms": 1},'
        '"nope"'
        "]}",
        encoding="utf-8",
    )
    loaded = ChatJobStore(tmp_path).load("chat-a")
    assert tuple(row.job_id for row in loaded) == ("j1",)


def test_none_folder_disables_load_and_save(tmp_path: Path) -> None:
    store = ChatJobStore(None)
    store.save("chat-a", (job("j1"),))
    assert store.load("chat-a") == ()
    assert list(tmp_path.iterdir()) == []


def test_unsafe_chat_name_maps_to_safe_file_name(tmp_path: Path) -> None:
    store = ChatJobStore(tmp_path)
    jobs = (job("j1"),)
    store.save("weird/name:with chars?", jobs)
    assert (tmp_path / "weird_name_with_chars_.json").is_file()
    assert store.load("weird/name:with chars?") == jobs


def test_unsafe_name_with_kind_keeps_job_kind_round_trip(tmp_path: Path) -> None:
    store = ChatJobStore(tmp_path)
    glm = ChatJob(
        job_id="j9",
        kind=KIND_GLM_SESSION,
        chat="a b",
        started_by="user",
        state=STATE_RUNNING,
        result="",
        started_ms=1,
        updated_ms=2,
    )
    store.save("a b", (glm,))
    assert store.load("a b") == (glm,)
