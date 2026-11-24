"""Tests for AllModsPingJob: pinging across mods, one bad mod skipped."""

from __future__ import annotations

from pathlib import Path

import pytest

from workbench.core.config import ModConfig, ModError
from workbench.notices.loop_tracker import LoopTracker
from workbench.notices.notice_dispatcher import NoticeDispatcher
from workbench.notices.notice_types import DeliveryRecord, Notice
from workbench.notices.owner_id import OwnerId, OwnerKind
from workbench.notices.owner_inbox import OwnerInbox
from workbench.server import all_mods_ping_job
from workbench.server.all_mods_ping_job import AllModsPingJob


class FakeRegistry:
    """Return one fixed list of discovery results."""

    def __init__(self, results: list[ModConfig | ModError]) -> None:
        self._results = results

    def all(self) -> list[ModConfig | ModError]:
        return self._results


class FakeTrackerFactory:
    """Build a throwaway tracker, or raise for the named mods."""

    def __init__(self, fail_for: set[str]) -> None:
        self._fail_for = fail_for

    def build(self, cfg: ModConfig) -> LoopTracker:
        if cfg.name in self._fail_for:
            raise RuntimeError("boom")
        return None  # type: ignore[return-value]


class FakeDispatcherFactory:
    """Build a throwaway dispatcher, or raise for the named mods."""

    def __init__(self, fail_for: set[str]) -> None:
        self._fail_for = fail_for

    def build(self, cfg: ModConfig) -> NoticeDispatcher:
        if cfg.name in self._fail_for:
            raise RuntimeError("boom")
        return None  # type: ignore[return-value]


def _install_pinger(monkeypatch: pytest.MonkeyPatch,
                    pinged: list[DeliveryRecord]) -> None:
    """Replace StuckPinger in the job module with a recording fake."""
    class FakePinger:
        """Record every record handed to ping_stuck and count it as sent."""

        def __init__(self, tracker: LoopTracker, inbox: OwnerInbox,
                     dispatcher: NoticeDispatcher) -> None:
            pass

        def ping_stuck(self, records: list[DeliveryRecord]) -> int:
            pinged.extend(records)
            return len(records)

    monkeypatch.setattr(all_mods_ping_job, "StuckPinger", FakePinger)


def _config(name: str, repo: Path) -> ModConfig:
    return ModConfig(name=name, repo=repo, platform=repo, screens=(),
                     boards=repo / "boards", status=repo / "status",
                     tracking=repo, log=repo, briefs=repo / "briefs",
                     exports=repo / "exports")


async def _unused_sleep(seconds: float) -> None:
    raise AssertionError("ping_all_once must not sleep")


def _stuck_records(repo: Path, count: int) -> None:
    inbox = OwnerInbox(repo / "status" / "inbox")
    for index in range(count):
        notice = Notice(id=f"n{index}",
                        owner=OwnerId(OwnerKind.PANE, "main-orchestrator"),
                        board="boards/open/b1", event="question",
                        file_path="boards/open/b1/board.md", line="",
                        created="2026-11-23T10:00:00")
        inbox.write(notice, True)


def test_one_raising_factory_does_not_stop_the_next(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pinged: list[DeliveryRecord] = []
    _install_pinger(monkeypatch, pinged)
    repo_a, repo_b = tmp_path / "repo-a", tmp_path / "repo-b"
    _stuck_records(repo_b, 2)
    job = AllModsPingJob(
        FakeRegistry([_config("ModA", repo_a), _config("ModB", repo_b)]),
        FakeTrackerFactory(fail_for={"ModA"}),
        FakeDispatcherFactory(fail_for=set()),
        _unused_sleep, interval_seconds=1.0)

    total = job.ping_all_once()

    assert total == 2
    assert len(pinged) == 2


def test_mod_errors_are_skipped(tmp_path: Path,
                                monkeypatch: pytest.MonkeyPatch) -> None:
    pinged: list[DeliveryRecord] = []
    _install_pinger(monkeypatch, pinged)
    repo_b = tmp_path / "repo-b"
    _stuck_records(repo_b, 1)
    job = AllModsPingJob(
        FakeRegistry([ModError(repo=tmp_path / "broken", reason="bad toml"),
                      _config("ModB", repo_b)]),
        FakeTrackerFactory(fail_for=set()),
        FakeDispatcherFactory(fail_for=set()),
        _unused_sleep, interval_seconds=1.0)

    assert job.ping_all_once() == 1
    assert len(pinged) == 1
