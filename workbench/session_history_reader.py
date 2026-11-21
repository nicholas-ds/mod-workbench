"""Saved chat session messages from the SDK (Task: chat history reload)."""

from __future__ import annotations

from collections.abc import Callable, Sequence


class SessionHistoryReader:
    """Fetch the saved messages of one session id through the SDK."""

    def __init__(self, fetch: Callable[[str, str], Sequence[object]]) -> None:
        self._fetch = fetch

    def read(self, session_id: str, folder: str) -> tuple[object, ...]:
        if session_id == "":
            return ()
        return tuple(self._fetch(session_id, folder))
