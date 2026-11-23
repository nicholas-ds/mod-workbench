"""Deliver notices to a chat thread through injected callables."""

from __future__ import annotations

from collections.abc import Callable

from workbench.notices.owner_id import OwnerKind, OwnerId
from workbench.notices.recipient import Recipient, RecipientTraits


class ChatRecipient(Recipient):
    """Send lines to and start fresh threads for a chat owner."""

    def __init__(self, send_turn: Callable[[str, str], bool],
                 context_of: Callable[[str], float | None],
                 is_known: Callable[[str], bool],
                 orchestrator_of: Callable[[str], str],
                 add_thread: Callable[[str], str]) -> None:
        self._send_turn = send_turn
        self._context_of = context_of
        self._is_known = is_known
        self._orchestrator_of = orchestrator_of
        self._add_thread = add_thread

    @property
    def traits(self) -> RecipientTraits:
        return RecipientTraits(kind=OwnerKind.CHAT,
                               label="App chat",
                               measures_context=True,
                               fresh_mode="new-thread",
                               retry_limit=5)

    def is_reachable(self, owner: OwnerId) -> bool:
        return self._is_known(owner.key)

    def context_percent(self, owner: OwnerId) -> float | None:
        return self._context_of(owner.key)

    def send_line(self, owner: OwnerId, line: str) -> bool:
        return self._send_turn(owner.key, line)

    def start_fresh(self, owner: OwnerId, prompt: str) -> bool:
        if not self._is_known(owner.key):
            return False
        thread = self._add_thread(self._orchestrator_of(owner.key))
        return self._send_turn(thread, prompt)
