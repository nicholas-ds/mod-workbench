"""List saved Claude sessions of a folder as /resume picker rows.

The SDK's ``list_sessions()`` returns ``SDKSessionInfo`` entries, newest
first. The picker needs ``SessionSummary`` rows: id, one-line title and
last modified time, with a title fallback chain for untitled sessions.
"""

from __future__ import annotations

from typing import Callable

from claude_agent_sdk import list_sessions

from workbench.session_summary import SessionSummary

_MAX_TITLE = 80
_FALLBACK_TITLE = "(untitled)"


class SessionHistoryLister:
    """Map the saved sessions of one folder to picker rows, newest first."""

    def __init__(
        self, list_function: Callable[..., list] = list_sessions, limit: int = 30
    ) -> None:
        self._list_function = list_function
        self._limit = limit

    def list(self, folder: str) -> tuple[SessionSummary, ...]:
        if not folder:
            return ()
        entries = self._list_function(directory=folder, limit=self._limit)
        rows: list[SessionSummary] = []
        for entry in entries:
            row = self._row_of(entry)
            if row is not None:
                rows.append(row)
        return tuple(rows)

    def _row_of(self, entry: object) -> SessionSummary | None:
        """One SDK entry as a row; entries without a session id give None."""
        session_id = getattr(entry, "session_id", None)
        if not isinstance(session_id, str) or not session_id:
            return None
        last_modified = getattr(entry, "last_modified", 0)
        return SessionSummary(
            session_id=session_id,
            title=self._title_of(entry),
            last_modified_ms=last_modified if isinstance(last_modified, int) else 0,
        )

    def _title_of(self, entry: object) -> str:
        """First non-empty of custom_title, summary, first_prompt, else a stub."""
        for name in ("custom_title", "summary", "first_prompt"):
            value = getattr(entry, name, None)
            if isinstance(value, str) and value:
                return " ".join(value.splitlines())[:_MAX_TITLE]
        return _FALLBACK_TITLE
