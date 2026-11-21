"""One saved chat session as one row in the /resume picker."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SessionSummary:
    """Boundary type: maps one to one to JSON."""

    session_id: str
    title: str
    last_modified_ms: int
