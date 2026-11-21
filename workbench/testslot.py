"""Test slot config, backup, restore and verify (game-testing.md section 5, steps 1 to 4)."""

from __future__ import annotations

import hashlib
import shutil
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

REQUIRED_FIELDS = (
    "baseline",
    "baseline_sha256",
    "saves_dir",
    "quicksave_name",
    "backups_dir",
    "keep",
)
_PATH_FIELDS = ("baseline", "saves_dir", "backups_dir")
_TEXT_FIELDS = ("baseline_sha256", "quicksave_name")


class SlotError(Exception):
    """A test slot config, restore or verify step failed."""


@dataclass(frozen=True)
class SlotConfig:
    baseline: Path
    baseline_sha256: str
    saves_dir: Path
    quicksave_name: str
    backups_dir: Path
    keep: int


class SlotConfigLoader:
    """Read `testing.toml` into a `SlotConfig`."""

    def load(self, path: Path) -> SlotConfig:
        raw = self._read(path)
        self._reject_missing_fields(raw, path)
        return self._build(raw, path)

    def _read(self, path: Path) -> dict[str, object]:
        if not path.is_file():
            raise SlotError(f"no config file at {path}")
        try:
            return tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
            raise SlotError(f"cannot read {path}: {exc}") from exc

    def _reject_missing_fields(self, raw: dict[str, object], path: Path) -> None:
        missing = [field for field in REQUIRED_FIELDS if field not in raw]
        if missing:
            raise SlotError(f"{path} misses fields: {', '.join(missing)}")

    def _build(self, raw: dict[str, object], path: Path) -> SlotConfig:
        root = path.resolve().parent
        for field in _PATH_FIELDS + _TEXT_FIELDS:
            if not isinstance(raw[field], str):
                raise SlotError(f"{path}: {field} must be a string")
        keep = raw["keep"]
        if not isinstance(keep, int) or isinstance(keep, bool) or keep < 1:
            raise SlotError(f"{path}: keep must be an integer of 1 or more")
        return SlotConfig(
            baseline=(root / str(raw["baseline"])).resolve(),
            baseline_sha256=str(raw["baseline_sha256"]),
            saves_dir=(root / str(raw["saves_dir"])).resolve(),
            quicksave_name=str(raw["quicksave_name"]),
            backups_dir=(root / str(raw["backups_dir"])).resolve(),
            keep=keep,
        )


class FileHasher:
    """SHA-256 of one file, read in blocks."""

    def sha256(self, path: Path) -> str:
        digest = hashlib.sha256()
        try:
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1 << 20), b""):
                    digest.update(block)
        except OSError as exc:
            raise SlotError(f"cannot read {path}: {exc}") from exc
        return digest.hexdigest()


class DirSnapshotter:
    """Snapshot one folder: file name to size and mtime in ns."""

    def snapshot(
        self, path: Path, exclude: frozenset[str]
    ) -> Mapping[str, tuple[int, int]]:
        if not path.is_dir():
            raise SlotError(f"no save folder at {path}")
        return {
            child.name: (child.stat().st_size, child.stat().st_mtime_ns)
            for child in sorted(path.iterdir())
            if child.is_file() and child.name not in exclude
        }


class SnapshotComparer:
    """Find the first alphabetical change between two folder snapshots."""

    def first_change(
        self,
        before: Mapping[str, tuple[int, int]],
        after: Mapping[str, tuple[int, int]],
    ) -> str | None:
        for name in sorted(set(before) | set(after)):
            if name not in after:
                return f"removed {name}"
            if name not in before:
                return f"added {name}"
            if before[name] != after[name]:
                return f"changed {name}"
        return None


class SaveBackupService:
    """Copy the save folder into a dated backup folder and keep the newest ones."""

    def backup(self, cfg: SlotConfig, now: str) -> Path:
        target = cfg.backups_dir / now
        try:
            cfg.backups_dir.mkdir(parents=True, exist_ok=True)
            shutil.copytree(cfg.saves_dir, target)
        except OSError as exc:
            raise SlotError(f"cannot back up saves to {target}: {exc}") from exc
        self._prune(cfg)
        return target

    def _prune(self, cfg: SlotConfig) -> None:
        try:
            backups = sorted(p for p in cfg.backups_dir.iterdir() if p.is_dir())
            for old in backups[:-cfg.keep]:
                shutil.rmtree(old)
        except OSError as exc:
            raise SlotError(f"cannot prune backups in {cfg.backups_dir}: {exc}") from exc


class MainSaveVerifier:
    """Reject any change to save files other than the test slot."""

    def __init__(self, snapshotter: DirSnapshotter, comparer: SnapshotComparer) -> None:
        self._snapshotter = snapshotter
        self._comparer = comparer

    def verify(self, cfg: SlotConfig, before: Mapping[str, tuple[int, int]]) -> None:
        after = self._snapshotter.snapshot(
            cfg.saves_dir, frozenset((cfg.quicksave_name,))
        )
        change = self._comparer.first_change(before, after)
        if change is not None:
            raise SlotError(f"main save folder changed: {change}")


class TestSlotRestorer:
    """Run game-testing.md section 5, steps 1 to 4, on the test slot."""

    __test__ = False  # pytest would otherwise collect this class by its name.
    def __init__(
        self,
        hasher: FileHasher,
        snapshotter: DirSnapshotter,
        backup_service: SaveBackupService,
        verifier: MainSaveVerifier,
    ) -> None:
        self._hasher = hasher
        self._snapshotter = snapshotter
        self._backup_service = backup_service
        self._verifier = verifier

    def restore(self, cfg: SlotConfig, now: str, dry_run: bool = False) -> list[str]:
        baseline_hash = self._checked_baseline_hash(cfg)
        if dry_run:
            return [self._baseline_action(cfg), *self._plan(cfg, now)]
        before = self._snapshotter.snapshot(
            cfg.saves_dir, frozenset((cfg.quicksave_name,))
        )
        backup_path = self._backup_service.backup(cfg, now)
        self._write_baseline(cfg, baseline_hash)
        self._verifier.verify(cfg, before)
        return [
            self._baseline_action(cfg),
            f"backed up saves to {backup_path}",
            f"wrote baseline to {self._quicksave_path(cfg)}",
            f"checked quicksave hash {baseline_hash}",
        ]

    def _quicksave_path(self, cfg: SlotConfig) -> Path:
        return cfg.saves_dir / cfg.quicksave_name

    def _checked_baseline_hash(self, cfg: SlotConfig) -> str:
        if not cfg.baseline.is_file():
            raise SlotError(f"no baseline file at {cfg.baseline}")
        actual = self._hasher.sha256(cfg.baseline)
        if actual.lower() != cfg.baseline_sha256.lower():
            raise SlotError(
                f"baseline hash {actual} does not match recorded hash "
                f"{cfg.baseline_sha256}"
            )
        return actual

    def _write_baseline(self, cfg: SlotConfig, baseline_hash: str) -> None:
        target = self._quicksave_path(cfg)
        try:
            shutil.copyfile(cfg.baseline, target)
        except OSError as exc:
            raise SlotError(f"cannot write {target}: {exc}") from exc
        written = self._hasher.sha256(target)
        if written != baseline_hash:
            raise SlotError(
                f"quicksave hash {written} does not match baseline hash {baseline_hash}"
            )

    def _baseline_action(self, cfg: SlotConfig) -> str:
        return f"verified baseline hash of {cfg.baseline}"

    def _plan(self, cfg: SlotConfig, now: str) -> list[str]:
        return [
            f"would back up saves to {cfg.backups_dir / now}",
            f"would write baseline to {self._quicksave_path(cfg)}",
        ]
