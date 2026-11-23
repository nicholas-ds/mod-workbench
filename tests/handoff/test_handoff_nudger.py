import asyncio

from workbench.handoff.handoff_nudger import HandoffMessageComposer, HandoffNudger
from workbench.handoff.handoff_types import FILES_KIND, REQUESTS_KIND, HandoffReport, HandoffRow


def make_row(kind: str, target: str, *items: str) -> HandoffRow:
    return HandoffRow(kind=kind, target=target, label=f"{target} {kind}", items=items)


class FakeScanner:
    def __init__(self, rows: tuple[HandoffRow, ...]) -> None:
        self._rows = rows

    def scan(self) -> HandoffReport:
        return HandoffReport(rows=self._rows, total=len(self._rows))


class RecordingRunner:
    def __init__(self) -> None:
        self.submitted: list[tuple[str, str]] = []

    async def submit(self, name: str, text: str) -> None:
        self.submitted.append((name, text))


def test_compose_requests_text_lists_the_items() -> None:
    row = make_row(REQUESTS_KIND, "CityBuilder", "measure ore rates", "map jump gates")
    text = HandoffMessageComposer().compose(row)
    assert text.startswith("[workbench handoff] ")
    assert "measure ore rates | map jump gates" in text
    assert "Read each requests.md line" in text


def test_compose_files_text_lists_the_items() -> None:
    row = make_row(FILES_KIND, "CityBuilder", "2026-11-18-ore.md", "2026-11-19-gates.md")
    text = HandoffMessageComposer().compose(row)
    assert text.startswith("[workbench handoff] ")
    assert "2026-11-18-ore.md, 2026-11-19-gates.md" in text
    assert "docs/research-handoff" in text


def test_nudge_submits_the_composed_text_to_the_target() -> None:
    row = make_row(FILES_KIND, "CityBuilder", "2026-11-18-ore.md")
    scanner = FakeScanner((make_row(REQUESTS_KIND, "main", "pick a target"), row))
    runner = RecordingRunner()
    nudger = HandoffNudger(scanner, HandoffMessageComposer(), runner)
    nudged = asyncio.run(nudger.nudge(FILES_KIND, "CityBuilder"))
    assert nudged is True
    assert runner.submitted == [("CityBuilder", HandoffMessageComposer().compose(row))]


def test_nudge_returns_false_and_submits_nothing_without_a_matching_row() -> None:
    scanner = FakeScanner((make_row(REQUESTS_KIND, "main", "pick a target"),))
    runner = RecordingRunner()
    nudger = HandoffNudger(scanner, HandoffMessageComposer(), runner)
    nudged = asyncio.run(nudger.nudge(FILES_KIND, "Nobody"))
    assert nudged is False
    assert runner.submitted == []
