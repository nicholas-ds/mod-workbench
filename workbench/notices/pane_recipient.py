"""Deliver notices to the main orchestrator pane."""

from __future__ import annotations

from collections.abc import Callable

from workbench.notices.owner_id import OwnerKind, OwnerId
from workbench.notices.pane_context_reader import PaneContextReader
from workbench.notices.recipient import Recipient, RecipientTraits
from workbench.panes.pane_registry import OrchestratorPane
from workbench.panes.pane_sender import PaneSender


class PaneRecipient(Recipient):
    """Send lines to and clear the orchestrator pane."""

    def __init__(self, find_pane: Callable[[OwnerId], OrchestratorPane | None],
                 sender: PaneSender, context_reader: PaneContextReader,
                 is_idle: Callable[[OwnerId], bool]) -> None:
        self._find_pane = find_pane
        self._sender = sender
        self._context_reader = context_reader
        self._is_idle = is_idle

    @property
    def traits(self) -> RecipientTraits:
        return RecipientTraits(kind=OwnerKind.PANE,
                               label="Claude Code pane",
                               measures_context=True,
                               fresh_mode="clear-pane",
                               retry_limit=5)

    def is_reachable(self, owner: OwnerId) -> bool:
        return self._find_pane(owner) is not None

    def context_percent(self, owner: OwnerId) -> float | None:
        return self._context_reader.read(owner)

    def send_line(self, owner: OwnerId, line: str) -> bool:
        pane = self._find_pane(owner)
        if pane is None:
            return False
        return self._sender.send(pane, line)

    def start_fresh(self, owner: OwnerId, prompt: str) -> bool:
        pane = self._find_pane(owner)
        if pane is None or not self._is_idle(owner):
            return False
        if not self._sender.send(pane, "/clear"):
            return False
        return self._sender.send(pane, prompt)
