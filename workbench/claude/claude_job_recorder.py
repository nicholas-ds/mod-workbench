"""ClaudeJobRecorder: turn Claude task messages into ChatJob rows (Task T2).

Pure apart from the clock: record takes the chat name, one SDK message and
the chat's job tuple, and returns the updated tuple. It never touches the
store; the caller decides when a change is worth saving.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from claude_agent_sdk import (
    TERMINAL_TASK_STATUSES,
    TaskNotificationMessage,
    TaskStartedMessage,
    TaskUpdatedMessage,
)

from workbench.chat.chat_job import KIND_CLAUDE_AGENT, STATE_RUNNING, ChatJob
from workbench.chat.chat_job_book import ChatJobBook


def _system_clock_ms() -> int:
    return int(time.time() * 1000)


class ClaudeJobRecorder:
    """Record Claude task messages into a chat's job tuple via ChatJobBook."""

    def __init__(
        self,
        job_book: ChatJobBook,
        clock_ms: Callable[[], int] = _system_clock_ms,
    ) -> None:
        self._job_book = job_book
        self._clock_ms = clock_ms

    def record(
        self, chat: str, message: object, jobs: tuple[ChatJob, ...]
    ) -> tuple[ChatJob, ...]:
        """Return the job tuple with the task message recorded; others pass through."""
        if isinstance(message, TaskStartedMessage):
            return self._record_started(chat, message, jobs)
        if isinstance(message, TaskNotificationMessage):
            return self._record_notification(message, jobs)
        if isinstance(message, TaskUpdatedMessage):
            return self._record_updated(message, jobs)
        return jobs

    def _record_started(
        self, chat: str, message: TaskStartedMessage, jobs: tuple[ChatJob, ...]
    ) -> tuple[ChatJob, ...]:
        now = self._clock_ms()
        job = ChatJob(
            job_id=message.task_id,
            kind=KIND_CLAUDE_AGENT,
            chat=chat,
            started_by="claude",
            state=STATE_RUNNING,
            result="",
            started_ms=now,
            updated_ms=now,
        )
        return self._job_book.add(jobs, job)

    def _record_notification(
        self, message: TaskNotificationMessage, jobs: tuple[ChatJob, ...]
    ) -> tuple[ChatJob, ...]:
        result = f"{message.status}: {message.summary}"
        return self._job_book.finish(jobs, message.task_id, result, self._clock_ms())

    def _record_updated(
        self, message: TaskUpdatedMessage, jobs: tuple[ChatJob, ...]
    ) -> tuple[ChatJob, ...]:
        status = self._terminal_status_of(message)
        if status is None:
            return jobs
        return self._job_book.finish(jobs, message.task_id, f"{status}", self._clock_ms())

    def _terminal_status_of(self, message: TaskUpdatedMessage) -> str | None:
        status = message.patch.get("status", message.status)
        if isinstance(status, str) and status in TERMINAL_TASK_STATUSES:
            return status
        return None
