"""Restore the baseline save into the test slot (game-testing.md section 2a)."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from workbench.testslot import (
    DirSnapshotter,
    FileHasher,
    MainSaveVerifier,
    SaveBackupService,
    SnapshotComparer,
    SlotConfigLoader,
    SlotError,
    TestSlotRestorer,
)

CONFIG_PATH = Path(__file__).resolve().parents[1] / "testing.toml"
VALID_FLAGS = frozenset(("--dry-run",))


class RestoreCli:
    """Run one restore command: one line per action, one line on failure."""

    def __init__(
        self,
        config_path: Path,
        loader: SlotConfigLoader,
        restorer: TestSlotRestorer,
    ) -> None:
        self._config_path = config_path
        self._loader = loader
        self._restorer = restorer

    def run(self, argv: list[str]) -> int:
        try:
            return self._restore(self._plan_only(argv))
        except SlotError as exc:
            print(f"restore failed: {exc}")
            return 1

    def _plan_only(self, argv: list[str]) -> bool:
        unknown = [arg for arg in argv if arg not in VALID_FLAGS]
        if unknown:
            raise SlotError(f"unknown argument {unknown[0]}")
        return "--dry-run" in argv

    def _restore(self, dry_run: bool) -> int:
        cfg = self._loader.load(self._config_path)
        actions = self._restorer.restore(cfg, self._timestamp(), dry_run)
        for action in actions:
            print(action)
        return 0

    def _timestamp(self) -> str:
        return datetime.now().strftime("%Y%m%d-%H%M%S")


def main() -> int:
    cli = RestoreCli(
        config_path=CONFIG_PATH,
        loader=SlotConfigLoader(),
        restorer=TestSlotRestorer(
            FileHasher(),
            DirSnapshotter(),
            SaveBackupService(),
            MainSaveVerifier(DirSnapshotter(), SnapshotComparer()),
        ),
    )
    return cli.run(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
