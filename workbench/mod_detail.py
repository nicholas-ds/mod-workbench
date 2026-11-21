"""Detail view data of one mod: file tails and folder names."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from workbench.config import ModConfig

_TAIL_LINES = 40


@dataclass(frozen=True)
class ModDetail:
    tracking_tail: tuple[str, ...]
    log_tail: tuple[str, ...]
    brief_names: tuple[str, ...]
    export_names: tuple[str, ...]


class ModDetailReader:
    """Read the file tails and folder names of one mod's detail view."""

    def read(self, cfg: ModConfig) -> ModDetail:
        return ModDetail(tracking_tail=self._tail(cfg.tracking), log_tail=self._tail(cfg.log),
                         brief_names=self._names(cfg.briefs), export_names=self._names(cfg.exports))

    def _tail(self, path: Path) -> tuple[str, ...]:
        if not path.is_file():
            return ()
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return tuple(lines[-_TAIL_LINES:])

    def _names(self, folder: Path) -> tuple[str, ...]:
        if not folder.is_dir():
            return ()
        return tuple(sorted(entry.name for entry in folder.iterdir()))
