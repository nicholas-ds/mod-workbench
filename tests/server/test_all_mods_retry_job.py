"""Tests for AllModsRetryJob: redelivery across mods, one bad mod skipped."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from workbench.core.config import ModConfig, ModError
from workbench.notices.notice_dispatcher import NoticeDispatcher
from workbench.notices.notice_types import DeliveryRecord, Notice
from workbench.notices.owner_id import OwnerId, OwnerKind
from workbench.notices.owner_inbox import OwnerInbox
from workbench.server.all_mods_retry_job import AllModsRetryJob


class FakeRegistry:
    """Return one fixed list of discovery results."""

    def __init__(self, results: list[ModConfig | ModError]) -> None:
        self._results = results

    def all(self) -> list[ModConfig | ModError]:
        return self._results


class FakeDispatcher:
    """Record every record handed to redeliver."""

    def __init__(self, redelivered: list[DeliveryRecord]) -> None:
        self._redelivered = redelivered

    def redeliver(self, record: DeliveryRecord) -> DeliveryRecord:
        self._redelivered.append(record)
        return record


class FakeDispatcherFactory:
    """Build a recording dispatcher, or raise for the named mods."""

    def __init__(self, redelivered: list[DeliveryRecord],
                 fail_for: set[str]) -> None:
        self._redelivered = redelivered
        self._fail_for = fail_for

    def build(self, cfg: ModConfig) -> NoticeDispatcher:
        if cfg.name in self._fail_for:
            raise RuntimeError("boom")
        return FakeDispatcher(self._redelivered)  # type: ignore[return-value]


def _config(name: str, repo: Path) -> ModConfig:
    return ModConfig(name=name, repo=repo, platform=repo, screens=(),
                     boards=repo / "boards", status=repo / "status",
                     tracking=repo, log=repo, briefs=repo / "briefs",
                     exports=repo / "exports")


async def _unused_sleep(seconds: float) -> None:
    raise AssertionError("retry_all_once must not sleep")


def _pending_records(repo: Path, count: int) -> None:
    inbox = OwnerInbox(repo / "status" / "inbox")
    for index in range(count):
        notice = Notice(id=f"n{index}",
                        owner=OwnerId(OwnerKind.PANE, "main-orchestrator"),
                        board="boards/open/b1", event="question",
                        file_path="boards/open/b1/board.md", line="",
                        created="2026-11-23T10:00:00")
        inbox.write(notice, True)


def test_one_raising_mod_does_not_stop_the_next(tmp_path: Path) -> None:
    redelivered: list[DeliveryRecord] = []
    repo_a, repo_b = tmp_path / "repo-a", tmp_path / "repo-b"
    _pending_records(repo_b, 2)
    job = AllModsRetryJob(
        FakeRegistry([_config("ModA", repo_a), _config("ModB", repo_b)]),
        FakeDispatcherFactory(redelivered, fail_for={"ModA"}),
        _unused_sleep, interval_seconds=1.0)

    total = job.retry_all_once()

    assert total == 2
    assert len(redelivered) == 2


def test_mod_errors_are_skipped(tmp_path: Path) -> None:
    redelivered: list[DeliveryRecord] = []
    repo_b = tmp_path / "repo-b"
    _pending_records(repo_b, 1)
    job = AllModsRetryJob(
        FakeRegistry([ModError(repo=tmp_path / "broken", reason="bad toml"),
                      _config("ModB", repo_b)]),
        FakeDispatcherFactory(redelivered, fail_for=set()),
        _unused_sleep, interval_seconds=1.0)

    assert job.retry_all_once() == 1


def test_run_loops_until_sleep_is_cancelled(tmp_path: Path) -> None:
    redelivered: list[DeliveryRecord] = []
    repo_a = tmp_path / "repo-a"
    _pending_records(repo_a, 1)
    intervals: list[float] = []

    async def sleep(seconds: float) -> None:
        intervals.append(seconds)
        if len(intervals) == 2:
            raise asyncio.CancelledError

    job = AllModsRetryJob(
        FakeRegistry([_config("ModA", repo_a)]),
        FakeDispatcherFactory(redelivered, fail_for=set()),
        sleep, interval_seconds=7.5)

    async def drive() -> None:
        await job.run()

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(drive())

    assert intervals == [7.5, 7.5]
    assert len(redelivered) == 2
