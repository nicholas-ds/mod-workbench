"""Watch file system paths and report batches of changed files."""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

from watchfiles import Change, awatch


class FileChangeWatcher:
    """Turn file system events for given paths into batches of changed paths."""

    async def changes(self, paths: list[Path]) -> AsyncIterator[frozenset[Path]]:
        async for batch in awatch(*paths):
            yield self._paths_of(batch)

    @staticmethod
    def _paths_of(batch: set[tuple[Change, str]]) -> frozenset[Path]:
        return frozenset(Path(path) for _, path in batch)
