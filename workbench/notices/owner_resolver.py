"""Resolve the owner of a board from the stamp, the raiser or a fallback."""

from __future__ import annotations

from collections.abc import Callable
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

    def __init__(self, store: BoardOwnerStore, fallback: OwnerId,
                 is_reachable: Callable[[OwnerId], bool]) -> None:
        self._store = store
        self._fallback = fallback
        self._is_reachable = is_reachable

    def resolve(self, board: Board) -> OwnerResolution:
        """Try the store stamp, then raised_by; an unreachable owner gets the fallback."""
        named = self._store.read(board.folder) or self._parse_raised_by(board.raised_by)
        if named is not None and self._is_reachable(named):
            return OwnerResolution(named, True)
        return OwnerResolution(self._fallback, False)

    @staticmethod
    def _parse_raised_by(raised_by: str | None) -> OwnerId | None:
        if not raised_by:
            return None
        try:
            return OwnerId.parse(raised_by)
        except ValueError:
            return None
