"""ChatJob: one background job row of a chat, frozen and JSON-shaped (Task T1).

Fields map one to one to the rows saved in the chat job file.
"""

from __future__ import annotations

from dataclasses import dataclass

KIND_CLAUDE_AGENT = "claude_agent"
KIND_GLM_SESSION = "glm_session"

STATE_RUNNING = "running"
STATE_FINISHED = "finished"
STATE_STOPPED = "stopped"
STATE_LOST = "lost"


@dataclass(frozen=True)
class ChatJob:
    """One background job started from a chat."""

    job_id: str
    kind: str
    chat: str
    started_by: str
    state: str
    result: str
    started_ms: int
    updated_ms: int
