from dataclasses import asdict

from fastapi import FastAPI
from fastapi.testclient import TestClient

from workbench.handoff_types import FILES_KIND, REQUESTS_KIND, HandoffReport, HandoffRow
from workbench.routes_handoff import HandoffRoutes


def make_row(kind: str, target: str, *items: str) -> HandoffRow:
    return HandoffRow(kind=kind, target=target, label=f"{target} {kind}", items=items)


class FakeScanner:
    def __init__(self, rows: tuple[HandoffRow, ...]) -> None:
        self._rows = rows

    def scan(self) -> HandoffReport:
        return HandoffReport(rows=self._rows, total=len(self._rows))


class FakeNudger:
    def __init__(self, nudged: bool) -> None:
        self._nudged = nudged
        self.calls: list[tuple[str, str]] = []

    async def nudge(self, kind: str, target: str) -> bool:
        self.calls.append((kind, target))
        return self._nudged


def make_client(nudged: bool) -> tuple[TestClient, FakeNudger]:
    rows = (make_row(REQUESTS_KIND, "main", "pick a target"),
            make_row(FILES_KIND, "CityBuilder", "2026-11-18-ore.md"))
    nudger = FakeNudger(nudged)
    app = FastAPI()
    app.include_router(HandoffRoutes(FakeScanner(rows), nudger).routes)
    return TestClient(app), nudger


def test_get_handoff_returns_the_report_rows() -> None:
    client, _ = make_client(True)
    response = client.get("/api/handoff")
    assert response.status_code == 200
    assert response.json() == {
        "rows": [
            {"kind": "requests", "target": "main", "label": "main requests",
             "items": ["pick a target"]},
            {"kind": "files", "target": "CityBuilder", "label": "CityBuilder files",
             "items": ["2026-11-18-ore.md"]},
        ],
        "total": 2,
    }


def test_post_nudge_submits_the_body_kind_and_target() -> None:
    client, nudger = make_client(True)
    response = client.post("/api/handoff/nudge",
                           json={"kind": "files", "target": "CityBuilder"})
    assert response.status_code == 200
    assert response.json() == {"nudged": True}
    assert nudger.calls == [("files", "CityBuilder")]


def test_post_nudge_returns_404_when_no_row_matches() -> None:
    client, _ = make_client(False)
    response = client.post("/api/handoff/nudge",
                           json={"kind": "requests", "target": "Nobody"})
    assert response.status_code == 404
