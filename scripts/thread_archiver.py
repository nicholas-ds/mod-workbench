"""SessionStart hook: archive cleared message files when the author runs /clear."""

from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

from stop_gate import WorkspaceLocator


class ThreadArchiver:
    """Move handled message files into a timestamped archive folder."""

    def archive(self, repo: Path, now: datetime) -> Path | None:
        archive = repo / "messages" / "archive" / now.strftime("%Y%m%dT%H%M%S")
        moves = self._collect_moves(archive)
        if not moves:
            return None
        for source, target in moves:
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.move(str(source), str(target))
            except OSError:
                continue
        return archive

    def _collect_moves(self, archive: Path) -> list[tuple[Path, Path]]:
        messages = archive.parent.parent
        moves: list[tuple[Path, Path]] = []
        for subfolder in ("done", "replies"):
            moves.extend(self._move_pairs(messages / subfolder, archive / subfolder))
        moves.extend(self._cli_move_pairs(messages, archive))
        return moves

    def _move_pairs(self, folder: Path, target: Path) -> list[tuple[Path, Path]]:
        if not folder.is_dir():
            return []
        return [(path, target / path.name) for path in sorted(folder.glob("*.md"))]

    def _cli_move_pairs(self, messages: Path, archive: Path) -> list[tuple[Path, Path]]:
        if not messages.is_dir():
            return []
        return [
            (path, archive / path.name)
            for path in sorted(messages.glob("*.md"))
            if self._has_cli_view(path)
        ]

    def _has_cli_view(self, path: Path) -> bool:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return False
        if not lines or lines[0].strip() != "---":
            return False
        for line in lines[1:]:
            stripped = line.strip()
            if stripped == "---":
                return False
            if stripped == "view: cli":
                return True
        return False


def handle_session_start(payload: dict, surface_id: str, root: Path) -> None:
    if payload.get("source") != "clear":
        return
    workspace = WorkspaceLocator().locate(root, surface_id)
    if workspace is not None:
        ThreadArchiver().archive(workspace.repo, datetime.now(timezone.utc))
