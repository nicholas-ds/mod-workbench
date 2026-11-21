"""Task overview of all mods, read from the master tracking file."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

_STALE_AFTER_DAYS = 2
_WAITS_MARKER = "waits: author"
_HEADING_PREFIX = "## "
_UPDATED_PREFIX = "updated:"
_DONE_PREFIX = "- [x]"
_OPEN_PREFIX = "- [ ]"
_NOT_FOUND_WARNING = "tracking.md not found"
_BOARD_MARKER = "board:"


@dataclass(frozen=True)
class TaskItem:
    text: str
    done: bool
    waits_for_author: bool


@dataclass(frozen=True)
class RepoTasks:
    mod: str
    updated: str | None
    items: tuple[TaskItem, ...]
    open_count: int
    warning: str | None


@dataclass(frozen=True)
class TaskOverview:
    repos: tuple[RepoTasks, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class Section:
    mod: str
    lines: tuple[str, ...]


@dataclass(frozen=True)
class UpdatedDate:
    text: str | None
    parsed: date | None


class TaskOverviewReader:
    """Read the master tracking file into a `TaskOverview`."""

    def read(self, path: Path, today: date,
             known_mods: tuple[str, ...]) -> TaskOverview:
        text = self._read_text(path)
        if text is None:
            return TaskOverview(repos=(), warnings=(_NOT_FOUND_WARNING,))
        sections = self._sections(text)
        repos = tuple(self._repo_tasks(section, today) for section in sections)
        warnings = (self._missing_mod_warnings(repos, known_mods)
                    + self._unboarded_warnings(repos))
        return TaskOverview(repos=repos, warnings=warnings)

    def _read_text(self, path: Path) -> str | None:
        try:
            return path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

    def _sections(self, text: str) -> tuple[Section, ...]:
        chunks = re.split(r"(?m)^## ", text)[1:]
        return tuple(self._section(chunk) for chunk in chunks)

    def _section(self, chunk: str) -> Section:
        name, _, body = chunk.partition("\n")
        return Section(mod=name.strip(), lines=tuple(body.splitlines()))

    def _repo_tasks(self, section: Section, today: date) -> RepoTasks:
        updated = self._updated(section.lines)
        items = self._items(section.lines)
        return RepoTasks(mod=section.mod, updated=updated.text, items=items,
                         open_count=sum(not item.done for item in items),
                         warning=self._warning(updated, today))

    def _updated(self, lines: tuple[str, ...]) -> UpdatedDate:
        line = next((entry for entry in lines
                     if entry.strip().startswith(_UPDATED_PREFIX)), None)
        if line is None:
            return UpdatedDate(text=None, parsed=None)
        value = line.split(":", 1)[1].strip()
        try:
            return UpdatedDate(text=value, parsed=date.fromisoformat(value))
        except ValueError:
            return UpdatedDate(text=None, parsed=None)

    def _warning(self, updated: UpdatedDate, today: date) -> str | None:
        if updated.parsed is None:
            return "no updated date"
        age = (today - updated.parsed).days
        if age > _STALE_AFTER_DAYS:
            return f"stale: updated {age} days ago"
        return None

    def _items(self, lines: tuple[str, ...]) -> tuple[TaskItem, ...]:
        parsed = (self._item(line) for line in lines)
        return tuple(item for item in parsed if item is not None)

    def _item(self, line: str) -> TaskItem | None:
        stripped = line.strip()
        if stripped.startswith(_DONE_PREFIX):
            return self._task(stripped.removeprefix(_DONE_PREFIX).strip(), done=True)
        if stripped.startswith(_OPEN_PREFIX):
            return self._task(stripped.removeprefix(_OPEN_PREFIX).strip(), done=False)
        return None

    def _task(self, text: str, done: bool) -> TaskItem:
        return TaskItem(text=text, done=done,
                        waits_for_author=_WAITS_MARKER in text.lower())

    def _missing_mod_warnings(self, repos: tuple[RepoTasks, ...],
                              known_mods: tuple[str, ...]) -> tuple[str, ...]:
        found = {repo.mod for repo in repos}
        return tuple(f"{name}: no section in tracking.md"
                     for name in known_mods if name not in found)

    def _unboarded_warnings(self, repos: tuple[RepoTasks, ...]) -> tuple[str, ...]:
        return tuple(f"{repo.mod}: waits on author with no board: {item.text[:50]}"
                     for repo in repos for item in repo.items
                     if not item.done and item.waits_for_author
                     and _BOARD_MARKER not in item.text.lower())
