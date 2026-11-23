"""Safe board item file resolution and item kind detection."""

from __future__ import annotations

from pathlib import Path

from workbench.boards.board_types import BoardError

_KIND_SUFFIXES: tuple[tuple[str, frozenset[str]], ...] = (
    ("image", frozenset({".png", ".jpg", ".jpeg", ".webp", ".gif"})),
    ("swf", frozenset({".swf"})),
    ("html", frozenset({".html", ".htm"})),
    ("svg", frozenset({".svg"})),
    ("text", frozenset({".txt", ".md"})),
)


class SafeItemResolver:
    """Resolve one board item file to a path inside its board folder."""

    def resolve(self, folder: Path, item_file: str) -> Path:
        resolved = (folder / item_file).resolve()
        if not resolved.is_relative_to(folder.resolve()):
            raise BoardError(folder, f"item file escapes the board folder: {item_file}")
        if not resolved.is_file():
            raise BoardError(folder, f"item file is missing in the board folder: {item_file}")
        return resolved


class ItemKindDetector:
    """Detect the viewer kind of one item file by extension."""

    def detect(self, path: Path) -> str:
        suffix = path.suffix.lower()
        for kind, suffixes in _KIND_SUFFIXES:
            if suffix in suffixes:
                return kind
        return "other"
