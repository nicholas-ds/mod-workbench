"""Zips qualifying done boards losslessly.

Spec: docs/board-archive-design.md, revision 1. Writes
boards/archive/<board id>.zip, verifies it, and only then removes the
board folder. Never raises; failures come back as an error string.
"""

from __future__ import annotations

import os
import shutil
import zipfile
from pathlib import Path

from workbench.archive_types import ArchiveCandidate, BoardArchiveResult

ARCHIVE_DIR_NAME = "archive"


class BoardZipper:
    def archive(
        self, candidate: ArchiveCandidate, boards_dir: Path, apply: bool
    ) -> BoardArchiveResult:
        board_dir = candidate.board_dir
        file_list = self._file_list(board_dir)
        file_count = len(file_list)
        total_bytes = sum(path.stat().st_size for path in file_list)
        counts = dict(board_dir=board_dir, file_count=file_count, total_bytes=total_bytes)
        target = boards_dir / ARCHIVE_DIR_NAME / f"{board_dir.name}.zip"
        if not apply:
            return BoardArchiveResult(archived=False, **counts)
        if target.exists():
            return BoardArchiveResult(
                archived=False, error="zip already exists", **counts
            )
        tmp_path = Path(str(target) + ".tmp")
        try:
            self._write_zip(board_dir, file_list, tmp_path)
            if not self._verify_zip(board_dir, file_list, tmp_path):
                raise ValueError("verify failed")
            os.replace(tmp_path, target)
            shutil.rmtree(board_dir)
        except Exception as exc:  # never raise to the caller
            if tmp_path.exists():
                tmp_path.unlink()
            return BoardArchiveResult(
                archived=False, error=str(exc), **counts
            )
        return BoardArchiveResult(archived=True, **counts)

    def _file_list(self, board_dir: Path) -> list[Path]:
        return sorted(p for p in board_dir.rglob("*") if p.is_file())

    def _write_zip(
        self, board_dir: Path, file_list: list[Path], tmp_path: Path
    ) -> None:
        tmp_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(tmp_path, "w", compression=zipfile.ZIP_LZMA) as zf:
            for path in file_list:
                name = board_dir.name + "/" + path.relative_to(board_dir).as_posix()
                zf.write(path, arcname=name)

    def _verify_zip(
        self, board_dir: Path, file_list: list[Path], tmp_path: Path
    ) -> bool:
        try:
            with zipfile.ZipFile(tmp_path) as zf:
                if zf.testzip() is not None:
                    return False
                in_zip = {(info.filename, info.file_size) for info in zf.infolist()}
        except Exception:
            return False
        on_disk = {
            (board_dir.name + "/" + path.relative_to(board_dir).as_posix(), path.stat().st_size)
            for path in file_list
        }
        return in_zip == on_disk
