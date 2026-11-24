"""Compose the one-line notice text for a board event."""

from __future__ import annotations

from workbench.notices.notice_types import Notice
from workbench.notices.owner_id import OwnerId


class NoticeComposer:
    """Build Notice value objects. Pure: no clock, no disk."""

    def compose(
        self,
        notice_id: str,
        event: str,
        board_id: str,
        owner: OwnerId,
        file_path: str,
        created: str,
    ) -> Notice:
        """Bind one board event to its owner with the exact notice line."""
        line = f"[workbench] board={board_id} event={event}. Read {file_path}."
        return Notice(
            id=notice_id,
            owner=owner,
            board=board_id,
            event=event,
            file_path=file_path,
            line=line,
            created=created,
        )

    def compose_ping(
        self,
        notice_id: str,
        board_id: str,
        owner: OwnerId,
        file_path: str,
        created: str,
    ) -> Notice:
        """Bind the stuck event to its owner with the exact ping line."""
        line = (f"[workbench] board={board_id} event=stuck. "
                f"You did not reply to the answers of board {board_id}. "
                "Say why in one line on the board, or run /handoff. "
                f"Read {file_path}.")
        return Notice(
            id=notice_id,
            owner=owner,
            board=board_id,
            event="stuck",
            file_path=file_path,
            line=line,
            created=created,
        )
