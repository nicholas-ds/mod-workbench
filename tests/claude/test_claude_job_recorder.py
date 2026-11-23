"""Tests for ClaudeJobRecorder: task messages become ChatJob rows."""

from claude_agent_sdk import TaskNotificationMessage, TaskStartedMessage, TaskUpdatedMessage

from runner_fakes import make_assistant

from workbench.chat.chat_job import KIND_CLAUDE_AGENT, STATE_FINISHED, STATE_RUNNING, ChatJob
from workbench.chat.chat_job_book import ChatJobBook
from workbench.claude.claude_job_recorder import ClaudeJobRecorder

NAME = "coder"


def make_recorder(*times: int) -> ClaudeJobRecorder:
    """Recorder whose clock hands out the given milliseconds in order."""
    ticks = iter(times)
    return ClaudeJobRecorder(ChatJobBook(), clock_ms=lambda: next(ticks))


def make_started(task_id: str = "t1") -> TaskStartedMessage:
    return TaskStartedMessage(
        subtype="task_started", data={}, task_id=task_id,
        description="refactor", uuid="u1", session_id="s1",
    )


def make_notification(task_id: str = "t1") -> TaskNotificationMessage:
    return TaskNotificationMessage(
        subtype="task_notification", data={}, task_id=task_id,
        status="completed", output_file="out.txt",
        summary="did the work", uuid="u1", session_id="s1",
    )


def running_row(task_id: str = "t1") -> ChatJob:
    return ChatJob(
        job_id=task_id, kind=KIND_CLAUDE_AGENT, chat=NAME, started_by="claude",
        state=STATE_RUNNING, result="", started_ms=100, updated_ms=100,
    )


def test_started_adds_a_running_row() -> None:
    recorder = make_recorder(500)
    jobs = recorder.record(NAME, make_started(), ())
    assert jobs == (
        ChatJob(
            job_id="t1", kind=KIND_CLAUDE_AGENT, chat=NAME, started_by="claude",
            state=STATE_RUNNING, result="", started_ms=500, updated_ms=500,
        ),
    )


def test_started_ms_comes_from_the_injected_clock() -> None:
    recorder = make_recorder(12345)
    jobs = recorder.record(NAME, make_started(), ())
    assert jobs[0].started_ms == 12345
    assert jobs[0].updated_ms == 12345


def test_notification_finishes_the_job_with_status_and_summary() -> None:
    recorder = make_recorder(100, 900)
    jobs = recorder.record(NAME, make_started(), ())
    finished = recorder.record(NAME, make_notification(), jobs)
    assert finished[0].state == STATE_FINISHED
    assert finished[0].result == "completed: did the work"
    assert finished[0].updated_ms == 900


def test_notification_for_unknown_id_leaves_rows_unchanged() -> None:
    recorder = make_recorder(100, 999)
    jobs = recorder.record(NAME, make_started(), ())
    finished = recorder.record(NAME, make_notification("other"), jobs)
    assert finished == jobs
    assert finished[0].updated_ms == 100


def test_terminal_task_updated_finishes_the_job() -> None:
    recorder = make_recorder(100, 700)
    jobs = recorder.record(NAME, make_started(), ())
    updated = TaskUpdatedMessage(subtype="task_updated", data={}, task_id="t1", patch={"status": "killed"})
    finished = recorder.record(NAME, updated, jobs)
    assert finished[0].state == STATE_FINISHED
    assert finished[0].result == "killed"
    assert finished[0].updated_ms == 700


def test_non_terminal_task_updated_changes_nothing() -> None:
    recorder = make_recorder(100, 999)
    jobs = recorder.record(NAME, make_started(), ())
    updated = TaskUpdatedMessage(subtype="task_updated", data={}, task_id="t1", patch={"status": "running"})
    assert recorder.record(NAME, updated, jobs) == jobs


def test_other_messages_change_nothing() -> None:
    recorder = make_recorder(100, 999)
    jobs = recorder.record(NAME, make_started(), ())
    assert recorder.record(NAME, make_assistant("hi"), jobs) == jobs
