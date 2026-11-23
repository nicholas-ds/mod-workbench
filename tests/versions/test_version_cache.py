"""Tests for the version cache."""

from pathlib import Path

from workbench.versions.version_cache import VersionCache
from workbench.versions.version_report import VersionReport


class FakeClock:
    def __init__(self, start: float = 1000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now


def make_report(name: str) -> VersionReport:
    return VersionReport(
        name=name,
        installed="1.0.0",
        latest="1.1.0",
        update_available=True,
        note="",
    )


def test_load_returns_saved_reports(tmp_path: Path) -> None:
    cache = VersionCache(tmp_path / "versions.json", 60, FakeClock())
    reports = (make_report("claude-agent-sdk"), make_report("claude-code"))
    cache.save(reports)
    assert cache.load() == reports


def test_stale_cache_loads_as_none(tmp_path: Path) -> None:
    clock = FakeClock()
    cache = VersionCache(tmp_path / "versions.json", 60, clock)
    cache.save((make_report("claude-agent-sdk"),))
    clock.now += 61
    assert cache.load() is None


def test_corrupt_cache_loads_as_none(tmp_path: Path) -> None:
    path = tmp_path / "versions.json"
    path.write_text("{not json", encoding="utf-8")
    cache = VersionCache(path, 60, FakeClock())
    assert cache.load() is None


def test_disabled_cache_saves_and_loads_nothing(tmp_path: Path) -> None:
    cache = VersionCache(None, 60, FakeClock())
    cache.save((make_report("claude-agent-sdk"),))
    assert cache.load() is None
