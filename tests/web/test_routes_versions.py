"""Route tests for VersionRoutes: cached GET, refresh POST, response shape."""

from dataclasses import asdict

from fastapi import FastAPI
from fastapi.testclient import TestClient

from workbench.web.routes_versions import VersionRoutes
from workbench.versions.version_report import VersionReport


def make_report(name: str) -> VersionReport:
    return VersionReport(
        name=name,
        installed="1.2.3",
        latest="1.3.0",
        update_available=True,
        note="",
    )


class FakeChecker:
    def __init__(self, reports: tuple[VersionReport, ...]) -> None:
        self._reports = reports
        self.calls = 0

    def check(self) -> tuple[VersionReport, ...]:
        self.calls += 1
        return self._reports


class FakeCache:
    def __init__(self, loaded: tuple[VersionReport, ...] | None) -> None:
        self._loaded = loaded
        self.saved: list[tuple[VersionReport, ...]] = []

    def load(self) -> tuple[VersionReport, ...] | None:
        return self._loaded

    def save(self, reports: tuple[VersionReport, ...]) -> None:
        self.saved.append(reports)


def make_client(cache: FakeCache) -> tuple[TestClient, FakeChecker]:
    checker = FakeChecker((make_report("claude-code"), make_report("opencode")))
    routes = VersionRoutes(checker, cache)
    app = FastAPI()
    app.include_router(routes.routes)
    return TestClient(app), checker


def test_get_uses_fresh_cache_without_checking() -> None:
    cached = (make_report("claude-code"), make_report("opencode"))
    client, checker = make_client(FakeCache(cached))
    response = client.get("/api/versions")
    assert response.status_code == 200
    assert checker.calls == 0
    assert response.json() == {"versions": [asdict(report) for report in cached]}


def test_get_checks_and_saves_when_cache_is_empty() -> None:
    cache = FakeCache(None)
    client, checker = make_client(cache)
    response = client.get("/api/versions")
    assert response.status_code == 200
    assert checker.calls == 1
    assert cache.saved == [(make_report("claude-code"), make_report("opencode"))]
    assert response.json()["versions"][0]["name"] == "claude-code"


def test_refresh_always_checks() -> None:
    cached = (make_report("claude-code"),)
    cache = FakeCache(cached)
    client, checker = make_client(cache)
    response = client.post("/api/versions/refresh")
    assert response.status_code == 200
    assert checker.calls == 1
    assert cache.saved == [(make_report("claude-code"), make_report("opencode"))]
    assert response.json()["versions"][0]["name"] == "claude-code"


def test_response_has_version_fields() -> None:
    client, _ = make_client(FakeCache(None))
    entry = client.get("/api/versions").json()["versions"][0]
    assert set(entry) == {"name", "installed", "latest", "update_available", "note"}
