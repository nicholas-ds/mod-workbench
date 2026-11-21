"""Create the thin config and the board folders for one mod repo."""

from __future__ import annotations

import os
from pathlib import Path

CONFIG_NAME = "workbench.toml"
_FOLDER_NAMES = ("boards/open", "boards/done", "status", "notes")


class ModInitializer:
    """Write workbench.toml once and create the board folders of one mod repo."""

    def init(self, repo: Path, name: str, platform: Path) -> list[Path]:
        repo = Path(repo)
        config_paths = self._write_config(repo, name, Path(platform))
        folder_paths = self._create_folders(repo)
        return [*config_paths, *folder_paths]

    def _write_config(self, repo: Path, name: str, platform: Path) -> list[Path]:
        config_path = repo / CONFIG_NAME
        if config_path.exists():
            return []
        config_path.write_text(self._toml_text(repo, name, platform), encoding="utf-8")
        return [config_path]

    def _create_folders(self, repo: Path) -> list[Path]:
        new_folders = [repo / relative for relative in _FOLDER_NAMES
                       if not (repo / relative).exists()]
        for folder in new_folders:
            folder.mkdir(parents=True)
        return new_folders

    def _toml_text(self, repo: Path, name: str, platform: Path) -> str:
        lines = [
            f'name = "{name}"',
            f'platform = "{self._relative(platform, repo)}"',
            "screens = []",
            'boards = "boards"',
            'status = "status"',
            'tracking = "tracking.md"',
            'log = "LOG.md"',
            'briefs = "briefs"',
            'exports = "exports"',
        ]
        return "\n".join(lines) + "\n"

    def _relative(self, target: Path, start: Path) -> str:
        try:
            return Path(os.path.relpath(target, start)).as_posix()
        except ValueError:
            # Windows cannot make two paths on different drives relative.
            return target.as_posix()
