import asyncio
from pathlib import Path

from workbench.chat.orchestrator_directory import OrchestratorEntry
from workbench.chat.wake_broadcaster import WAKE_TEXT, WakeBroadcaster


class FakeDirectory:
    def entries(self) -> tuple[OrchestratorEntry, ...]:
        return (OrchestratorEntry("main", "x"), OrchestratorEntry("CityBuilder", "y"))


class RecordingRunner:
    def __init__(self) -> None:
        self.submitted: list[tuple[str, str]] = []

    async def submit(self, name: str, text: str) -> None:
        self.submitted.append((name, text))


def test_wake_all_submits_the_wake_text_to_every_chat() -> None:
    runner = RecordingRunner()
    woken = asyncio.run(WakeBroadcaster(FakeDirectory(), runner).wake_all())
    assert woken == ("main", "CityBuilder")
    assert runner.submitted == [("main", WAKE_TEXT), ("CityBuilder", WAKE_TEXT)]
