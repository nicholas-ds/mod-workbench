"""Watch the roots and toast once for each new blocking board."""

from __future__ import annotations

from pathlib import Path

from workbench.boards.alerts import NewBoardTracker, ToastNotifier
from workbench.boards.board_repository import OPEN_STATE
from workbench.boards.board_types import BoardEntry
from workbench.core.config import ModConfig
from workbench.core.watch import FileChangeWatcher
from workbench.mods.mod_registry import ModRegistry


class BlockingBoardAlerter:
    """Watch the roots and toast once for each new blocking board."""

    def __init__(self, watcher: FileChangeWatcher, registry: ModRegistry,
                 roots: list[Path], tracker: NewBoardTracker,
                 notifier: ToastNotifier) -> None:
        self._watcher, self._registry = watcher, registry
        self._roots, self._tracker, self._notifier = roots, tracker, notifier

    async def run(self) -> None:
        async for _batch in self._watcher.changes(self._roots):
            self._alert_fresh()

    def _alert_fresh(self) -> None:
        for entry in self._tracker.new_blocking(self._open_entries()):
            self._notifier.notify("Blocking board", entry.board.title)

    def _open_entries(self) -> list[BoardEntry]:
        return [entry for cfg in self._mods() for entry in self._entries_of(cfg)]

    def _mods(self) -> list[ModConfig]:
        return [result for result in self._registry.all() if isinstance(result, ModConfig)]

    def _entries_of(self, cfg: ModConfig) -> list[BoardEntry]:
        listed = self._registry.entries(cfg, OPEN_STATE)
        return [entry for entry in listed if isinstance(entry, BoardEntry)]
