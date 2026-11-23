"""ChatJobBook: pure queries and updates over a tuple of ChatJob rows (Task T1).

No I/O and no hidden state: every method takes the jobs tuple and returns one.
"""

from __future__ import annotations

from dataclasses import replace

from workbench.chat.chat_job import KIND_CLAUDE_AGENT, STATE_FINISHED, STATE_RUNNING, STATE_STOPPED, ChatJob

_HEADER = "Background jobs of this chat:"


class ChatJobBook:
    """Pure helpers over job tuples; never mutates its input."""

    def add(self, jobs: tuple[ChatJob, ...], job: ChatJob) -> tuple[ChatJob, ...]:
        """Append job, or replace the row that shares its job_id in place."""
        for index, row in enumerate(jobs):
            if row.job_id == job.job_id:
                return jobs[:index] + (job,) + jobs[index + 1 :]
        return jobs + (job,)

    def finish(
        self, jobs: tuple[ChatJob, ...], job_id: str, result: str, now_ms: int
    ) -> tuple[ChatJob, ...]:
        """Mark the job finished with its result; an unknown id leaves all rows unchanged."""
        return tuple(
            replace(row, state=STATE_FINISHED, result=result, updated_ms=now_ms)
            if row.job_id == job_id
            else row
            for row in jobs
        )

    def stop_claude_jobs(self, jobs: tuple[ChatJob, ...], now_ms: int) -> tuple[ChatJob, ...]:
        """Stop running claude_agent jobs; every other row keeps its state."""
        return tuple(
            replace(row, state=STATE_STOPPED, updated_ms=now_ms)
            if row.kind == KIND_CLAUDE_AGENT and row.state == STATE_RUNNING
            else row
            for row in jobs
        )

    def running(self, jobs: tuple[ChatJob, ...]) -> tuple[ChatJob, ...]:
        """Return the rows whose state is running, in order."""
        return tuple(row for row in jobs if row.state == STATE_RUNNING)

    def summary(self, jobs: tuple[ChatJob, ...]) -> str:
        """One line per job under a header; an empty tuple gives an empty string."""
        if not jobs:
            return ""
        lines = [_HEADER]
        for row in jobs:
            line = f"{row.kind} {row.job_id} {row.state}"
            if row.result:
                line += f" -> {row.result}"
            lines.append(line)
        return "\n".join(lines)
