"""Resolve the owner of a board from the stamp, the raiser or a fallback."""

from __future__ import annotations

from dataclasses import dataclass

from workbench.boards.board_types import Board
from workbench.notices.board_owner_store import BoardOwnerStore
from workbench.notices.owner_id import OwnerId


@dataclass(frozen=True)
class OwnerResolution:
    """The resolved owner and whether it is trusted."""

    owner: OwnerId
    known: bool


class OwnerResolver:
    """Pick an owner for a board; never returns None and never raises."""

    def __init__(self, store: BoardOwnerStore, fallback: OwnerId) -> None:
        self._store = store
        self._fallback = fallback

    def resolve(self, board: Board) -> OwnerResolution:
        """Try the store stamp, then the old raised_by value, then the fallback."""
        stamped = self._store.read(board.folder)
        if stamped is not None:
            return OwnerResolution(stamped, True)
        raised = self._parse_raised_by(board.raised_by)
        if raised is not None:
            return OwnerResolution(raised, True)
        return OwnerResolution(self._fallback, False)

    @staticmethod
    def _parse_raised_by(raised_by: str | None) -> OwnerId | None:
        if not raised_by:
            return None
        try:
            return OwnerId.parse(raised_by)
        except ValueError:
            return None
