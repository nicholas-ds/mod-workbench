"""Scanner for research handoff items that wait, across all mod repos.

Each build repo may keep `docs/research-handoff/` with a `requests.md`
checklist and one topic `*.md` file per answered question. A topic file
still waits when no board or the repo's `tracking.md` mentions it. Read-only: nothing here writes
to disk.
"""

from __future__ import annotations

from pathlib import Path

from workbench.config import ModConfig
from workbench.handoff_types import (
    FILES_KIND,
    REQUESTS_KIND,
    HandoffReport,
    HandoffRow,
)
from workbench.mod_registry import ModRegistry

_REQUESTS_PREFIX = "- [open"
_IGNORED_FILES = ("README.md", "requests.md")
_HANDOFF_PARTS = ("docs", "research-handoff")
_BOARD_STATES = ("open", "done")


class OpenRequestReader:
    """Read the open request lines of one `requests.md`."""

    def read(self, requests_file: Path) -> tuple[str, ...]:
        if not requests_file.is_file():
            return ()
        text = requests_file.read_text(encoding="utf-8", errors="replace")
        lines = [raw.strip() for raw in text.splitlines()]
        return tuple(line for line in lines if line.startswith(_REQUESTS_PREFIX))


class UnpickedFileFinder:
    """List handoff topic files no board has picked up yet."""

    def find(self, handoff_dir: Path, board_texts: tuple[str, ...]) -> tuple[str, ...]:
        if not handoff_dir.is_dir():
            return ()
        return tuple(sorted(
            path.name
            for path in handoff_dir.glob("*.md")
            if path.name not in _IGNORED_FILES
            and not any(path.stem in text for text in board_texts)
        ))


class BoardTextReader:
    """Read the text of every board page under open and done."""

    def read(self, boards_dir: Path) -> tuple[str, ...]:
        if not boards_dir.is_dir():
            return ()
        texts: list[str] = []
        for state in _BOARD_STATES:
            for pattern in ("*/*.md", "*/*.html"):
                texts.extend(self._read(path) for path in sorted(boards_dir.glob(f"{state}/{pattern}")))
        return tuple(texts)

    def _read(self, path: Path) -> str:
        return path.read_text(encoding="utf-8", errors="replace")


class TrackingTextReader:
    """Read the text of one repo's tracking.md."""

    def read(self, tracking_file: Path) -> tuple[str, ...]:
        if not tracking_file.is_file():
            return ()
        return (tracking_file.read_text(encoding="utf-8", errors="replace"),)


class HandoffScanner:
    """Build the research handoff report from all build mod repos."""

    def __init__(
        self,
        registry: ModRegistry,
        research_mod: str,
        request_reader: OpenRequestReader,
        file_finder: UnpickedFileFinder,
        board_reader: BoardTextReader,
        tracking_reader: TrackingTextReader,
    ) -> None:
        self._registry = registry
        self._research_mod = research_mod
        self._request_reader = request_reader
        self._file_finder = file_finder
        self._board_reader = board_reader
        self._tracking_reader = tracking_reader

    def scan(self) -> HandoffReport:
        cfgs = [r for r in self._registry.all() if isinstance(r, ModConfig)]
        rows = [self._request_row(cfgs)] + [self._file_row(cfg) for cfg in cfgs]
        present = tuple(row for row in rows if row is not None)
        return HandoffReport(rows=present, total=sum(len(row.items) for row in present))

    def _request_row(self, cfgs: list[ModConfig]) -> HandoffRow | None:
        items: list[str] = []
        for cfg in cfgs:
            handoff_dir = cfg.repo.joinpath(*_HANDOFF_PARTS)
            if not handoff_dir.is_dir():
                continue
            for line in self._request_reader.read(handoff_dir / "requests.md"):
                items.append(f"{cfg.name}: {line}")
        if not items:
            return None
        return HandoffRow(kind=REQUESTS_KIND, target=self._research_mod, label="Research",
                          items=tuple(items))

    def _file_row(self, cfg: ModConfig) -> HandoffRow | None:
        handoff_dir = cfg.repo.joinpath(*_HANDOFF_PARTS)
        if not handoff_dir.is_dir():
            return None
        texts = self._board_reader.read(cfg.boards) + self._tracking_reader.read(cfg.tracking)
        items = self._file_finder.find(handoff_dir, texts)
        if not items:
            return None
        return HandoffRow(kind=FILES_KIND, target=cfg.name, label=cfg.name, items=items)
