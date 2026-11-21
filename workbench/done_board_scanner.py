"""Scanner for qualifying done boards.

Spec: docs/board-archive-design.md, revision 1. Finds done boards whose
newest file is old enough to archive. Read-only: nothing here writes to
disk.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from workbench.archive_policy import ArchivePolicy
from workbench.archive_types import ArchiveCandidate

DONE_DIR_NAME = "done"


class DoneBoardScanner:
    def scan(
        self, boards_dir: Path, policy: ArchivePolicy, now: datetime
    ) -> tuple[ArchiveCandidate, ...]:
        done_dir = boards_dir / DONE_DIR_NAME
        if not done_dir.is_dir():
            return ()
        candidates: list[ArchiveCandidate] = []
        for board_dir in sorted(p for p in done_dir.iterdir() if p.is_dir()):
            newest_mtime = self._newest_mtime(board_dir)
            if newest_mtime is None:
                continue
            newest = datetime.fromtimestamp(newest_mtime, tz=now.tzinfo)
            if now - newest < timedelta(days=policy.min_age_days):
                continue
            candidates.append(ArchiveCandidate(board_dir=board_dir))
        return tuple(candidates)

    def _newest_mtime(self, board_dir: Path) -> float | None:
        mtimes = [
            path.stat().st_mtime for path in board_dir.rglob("*") if path.is_file()
        ]
        return max(mtimes) if mtimes else None
