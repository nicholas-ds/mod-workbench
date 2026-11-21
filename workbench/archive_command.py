"""Command that zips old done boards and reports the result.

Spec: docs/board-archive-design.md, revision 1. Pure pipeline: no argparse
and no printing here; the caller wires, prints and maps the report to an
exit code.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from workbench.archive_policy import ArchivePolicy
from workbench.archive_report_writer import ArchiveReportWriter
from workbench.archive_types import BoardArchiveJob, BoardArchiveResult
from workbench.board_zipper import BoardZipper
from workbench.config import ModConfig, ModConfigLoader, ModDiscovery
from workbench.done_board_scanner import DoneBoardScanner


class ArchiveCommand:
    def __init__(
        self,
        discovery: ModDiscovery,
        scanner: DoneBoardScanner,
        zipper: BoardZipper,
        report_writer: ArchiveReportWriter,
        clock: Callable[[], datetime],
    ) -> None:
        self._discovery = discovery
        self._scanner = scanner
        self._zipper = zipper
        self._report_writer = report_writer
        self._clock = clock

    def run(self, roots: list[Path], days: int, apply: bool) -> str:
        policy = ArchivePolicy(min_age_days=days)
        jobs = self._jobs(self._boards_dirs(roots), policy)
        results = self._archive_all(jobs, apply)
        return self._report_writer.write(results, apply)

    def _boards_dirs(self, roots: list[Path]) -> list[Path]:
        discovered = self._discovery.discover(roots)
        return [
            config.boards for config in discovered if isinstance(config, ModConfig)
        ]

    def _jobs(
        self, boards_dirs: list[Path], policy: ArchivePolicy
    ) -> list[BoardArchiveJob]:
        now = self._clock()
        jobs: list[BoardArchiveJob] = []
        for boards_dir in boards_dirs:
            for candidate in self._scanner.scan(boards_dir, policy, now):
                jobs.append(
                    BoardArchiveJob(boards_dir=boards_dir, candidate=candidate)
                )
        return jobs

    def _archive_all(
        self, jobs: list[BoardArchiveJob], apply: bool
    ) -> tuple[BoardArchiveResult, ...]:
        return tuple(
            self._zipper.archive(job.candidate, job.boards_dir, apply)
            for job in jobs
        )


def build_archive_command() -> ArchiveCommand:
    """Wire the real archive parts with a tz-aware local-time clock."""

    def clock() -> datetime:
        return datetime.now(timezone.utc).astimezone()

    return ArchiveCommand(
        discovery=ModDiscovery(ModConfigLoader()),
        scanner=DoneBoardScanner(),
        zipper=BoardZipper(),
        report_writer=ArchiveReportWriter(),
        clock=clock,
    )
