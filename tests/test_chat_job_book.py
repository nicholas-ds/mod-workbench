"""Tests for the pure chat job book."""

from workbench.chat_job import (
    KIND_CLAUDE_AGENT,
    KIND_GLM_SESSION,
    STATE_FINISHED,
    STATE_LOST,
    STATE_RUNNING,
    STATE_STOPPED,
    ChatJob,
)
from workbench.chat_job_book import ChatJobBook


def job(
    job_id: str,
    kind: str = KIND_CLAUDE_AGENT,
    state: str = STATE_RUNNING,
    result: str = "",
) -> ChatJob:
    return ChatJob(
        job_id=job_id,
        kind=kind,
        chat="chat-a",
        started_by="agent",
        state=state,
        result=result,
        started_ms=100,
        updated_ms=100,
    )


def test_add_appends_new_and_replaces_same_id_in_place() -> None:
    book = ChatJobBook()
    first = job("j1")
    second = job("j2", kind=KIND_GLM_SESSION)
    jobs = book.add((), first)
    jobs = book.add(jobs, second)
    assert jobs == (first, second)
    done = job("j1", state=STATE_FINISHED, result="ok")
    jobs = book.add(jobs, done)
    assert jobs == (done, second)


def test_finish_sets_state_result_and_updated_ms() -> None:
    book = ChatJobBook()
    jobs = book.finish((job("j1"),), "j1", "done text", 500)
    assert jobs[0].state == STATE_FINISHED
    assert jobs[0].result == "done text"
    assert jobs[0].updated_ms == 500


def test_finish_with_unknown_id_leaves_jobs_unchanged() -> None:
    book = ChatJobBook()
    jobs = (job("j1"),)
    assert book.finish(jobs, "ghost", "nope", 500) == jobs


def test_stop_claude_jobs_only_hits_running_claude_rows() -> None:
    book = ChatJobBook()
    claude = job("j1")
    glm = job("j2", kind=KIND_GLM_SESSION)
    finished = job("j3", state=STATE_FINISHED, result="ok")
    lost = job("j4", state=STATE_LOST)
    jobs = book.stop_claude_jobs((claude, glm, finished, lost), 700)
    assert jobs[0].state == STATE_STOPPED
    assert jobs[0].updated_ms == 700
    assert jobs[1] == glm
    assert jobs[2] == finished
    assert jobs[3] == lost


def test_running_returns_only_running_rows_in_order() -> None:
    book = ChatJobBook()
    first = job("j1")
    second = job("j2", state=STATE_FINISHED, result="ok")
    third = job("j3")
    assert book.running((first, second, third)) == (first, third)


def test_summary_is_empty_without_jobs() -> None:
    assert ChatJobBook().summary(()) == ""


def test_summary_lists_each_job_and_marks_results() -> None:
    book = ChatJobBook()
    jobs = (job("j1"), job("j2", kind=KIND_GLM_SESSION, state=STATE_FINISHED, result="ok"))
    text = book.summary(jobs)
    assert text.splitlines() == [
        "Background jobs of this chat:",
        f"{KIND_CLAUDE_AGENT} j1 {STATE_RUNNING}",
        f"{KIND_GLM_SESSION} j2 {STATE_FINISHED} -> ok",
    ]
