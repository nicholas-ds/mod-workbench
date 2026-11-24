"""Deliver notices to a new chat session in the board's repo."""

from __future__ import annotations

from collections.abc import Callable

from workbench.notices.owner_id import OwnerKind, OwnerId
from workbench.notices.recipient import Recipient, RecipientTraits


class RepoSessionRecipient(Recipient):
    """Open a new chat thread in the repo named by the owner key, then send."""

    def __init__(self, send_turn: Callable[[str, str], bool],
                 add_thread: Callable[[str], str]) -> None:
        self._send_turn = send_turn
        self._add_thread = add_thread

    @property
    def traits(self) -> RecipientTraits:
        return RecipientTraits(kind=OwnerKind.REPO,
                               label="New session in the repo",
                               measures_context=False,
                               fresh_mode="new-thread",
                               retry_limit=5)

    def is_reachable(self, owner: OwnerId) -> bool:
        return True

    def context_percent(self, owner: OwnerId) -> float | None:
        return None

    def send_line(self, owner: OwnerId, line: str) -> bool:
        thread = self._add_thread(owner.key)
        return self._send_turn(thread, line)

    def start_fresh(self, owner: OwnerId, prompt: str) -> bool:
        return self.send_line(owner, prompt)
