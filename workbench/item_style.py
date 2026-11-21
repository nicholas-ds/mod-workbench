"""Add the workbench scrollbar style to HTML board items."""

from __future__ import annotations

import re
from pathlib import Path

_STYLE_FILES = ("tokens.css", "scrollbar.css")
_COLOR_SCHEME = re.compile(r"color-scheme\s*:[^;]*;")
_HEAD_CLOSE = re.compile(r"</head\s*>", re.IGNORECASE)


class HtmlItemStyler:
    """Inline the design tokens and scrollbar rules into one HTML item."""

    def __init__(self, web_dir: Path) -> None:
        self._web_dir = web_dir

    def apply(self, html: str) -> str:
        style = self._style_tag()
        match = _HEAD_CLOSE.search(html)
        if match is None:
            return style + html
        return html[:match.start()] + style + html[match.start():]

    def _style_tag(self) -> str:
        return f"<style>{self._css()}</style>"

    def _css(self) -> str:
        texts = (self._read(name) for name in _STYLE_FILES)
        return _COLOR_SCHEME.sub("", "\n".join(texts))

    def _read(self, name: str) -> str:
        try:
            return (self._web_dir / name).read_text(encoding="utf-8")
        except OSError:
            return ""
