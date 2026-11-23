"""The background job that runs the blocking board alerter loop."""

from __future__ import annotations

from workbench.server.background_job import BackgroundJob
from workbench.server.blocking_board_alerter import BlockingBoardAlerter


class AlertJob(BackgroundJob):
    """Run the blocking board alerter until cancelled."""

    def __init__(self, alerter: BlockingBoardAlerter) -> None:
        self._alerter = alerter

    async def run(self) -> None:
        await self._alerter.run()
