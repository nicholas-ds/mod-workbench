"""Send one wake-up turn to every orchestrator chat."""

from __future__ import annotations

from workbench.chat_turn_sink import TurnSubmitter
from workbench.orchestrator_directory import OrchestratorDirectory

WAKE_TEXT = (
    "[workbench wake] Wake-up call. "
    "Audit your section in E:/repos/mods/tracking.md and bring it up to date. "
    "Check for new work and new answers. "
    "Decide if anything needs the author: if so, raise a workbench board for it. "
    "If you are in the middle of work, ignore this and continue."
)


class WakeBroadcaster:
    """Submit the wake text to each chat. A busy chat queues it behind its turn."""

    def __init__(self, directory: OrchestratorDirectory, runner: TurnSubmitter) -> None:
        self._directory = directory
        self._runner = runner

    async def wake_all(self) -> tuple[str, ...]:
        names = tuple(entry.name for entry in self._directory.entries())
        for name in names:
            await self._runner.submit(name, WAKE_TEXT)
        return names
