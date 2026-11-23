"""Save one uploaded file into the uploads folder of a chat folder."""

from __future__ import annotations

import re
from pathlib import Path

_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]")


class ChatUploadSaver:
    """Write one uploaded file below <folder>/uploads/ under a safe name."""

    def __init__(self, max_bytes: int = 20 * 1024 * 1024) -> None:
        self._max_bytes = max_bytes

    @property
    def max_bytes(self) -> int:
        return self._max_bytes

    def save(self, folder: str, filename: str, data: bytes) -> str:
        if not folder:
            raise ValueError("folder is empty")
        if not data:
            raise ValueError("data is empty")
        if len(data) > self._max_bytes:
            raise ValueError("data exceeds max_bytes")
        uploads = Path(folder) / "uploads"
        uploads.mkdir(parents=True, exist_ok=True)
        self._write_gitignore(uploads)
        target = self._free_path(uploads / self._clean(filename))
        target.write_bytes(data)
        return target.as_posix()

    def _write_gitignore(self, uploads: Path) -> None:
        gitignore = uploads / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("*\n", encoding="utf-8")

    def _free_path(self, path: Path) -> Path:
        if not path.exists():
            return path
        number = 2
        while True:
            candidate = path.with_name(f"{path.stem}-{number}{path.suffix}")
            if not candidate.exists():
                return candidate
            number += 1

    def _clean(self, filename: str) -> str:
        name = filename.replace("\\", "/").split("/")[-1]
        name = _UNSAFE_CHARS.sub("_", name).lstrip(".")
        return name or "upload"
