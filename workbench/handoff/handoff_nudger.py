"""Nudge the chat that should act on one research handoff row."""

from __future__ import annotations

from typing import Protocol

from workbench.panes.chat_turn_sink import TurnSubmitter
from workbench.handoff.handoff_types import FILES_KIND, REQUESTS_KIND, HandoffReport, HandoffRow

REQUESTS_TEXT = (
    "[workbench handoff] "
    "Open research requests wait: {items}. "
    "Read each requests.md line. Run the research loop or answer it. "
    "Publish a handoff file when done. "
    "Raise a workbench board for each result or for any question to the author. "
    "If you are in the middle of work, finish it first."
)

FILES_TEXT = (
    "[workbench handoff] "
    "New research handoff files wait for this repo: {items}. "
    "Read each file in docs/research-handoff. "
    "Decide the build task or feedback to research (add a line to requests.md). "
    "Raise a workbench board for each, and name the handoff file on that board or in tracking.md: "
    "a board or tracking line that names the file marks it picked up. "
    "If you are in the middle of work, finish it first."
)

TEMPLATES = {
    REQUESTS_KIND: (REQUESTS_TEXT, " | "),
    FILES_KIND: (FILES_TEXT, ", "),
}


class HandoffScanSource(Protocol):
    def scan(self) -> HandoffReport: ...


class HandoffMessageComposer:
    """Compose the nudge text of one handoff row from its kind."""

    def compose(self, row: HandoffRow) -> str:
        template, joiner = TEMPLATES[row.kind]
        return template.format(items=joiner.join(row.items))


class HandoffNudger:
    """Submit one row's nudge text to the chat named by the row's target."""

    def __init__(self, scanner: HandoffScanSource, composer: HandoffMessageComposer,
                 runner: TurnSubmitter) -> None:
        self._scanner = scanner
        self._composer = composer
        self._runner = runner

    async def nudge(self, kind: str, target: str) -> bool:
        row = self._row_of(kind, target)
        if row is None:
            return False
        await self._runner.submit(target, self._composer.compose(row))
        return True

    def _row_of(self, kind: str, target: str) -> HandoffRow | None:
        for row in self._scanner.scan().rows:
            if row.kind == kind and row.target == target:
                return row
        return None
