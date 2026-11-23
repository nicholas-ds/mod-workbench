"""Split one file's front matter into fields and body."""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType

import yaml

from workbench.boards.board_types import BoardError, FrontMatter

_MARKER = "---"

_BOOL_TAG = "tag:yaml.org,2002:bool"
_TRUE_FALSE = re.compile(r"^(?:true|True|TRUE|false|False|FALSE)$")


class PlainBooleanLoader(yaml.SafeLoader):
    """Safe loader that reads only true/false (any case) as booleans."""


for _letter, _resolvers in list(PlainBooleanLoader.yaml_implicit_resolvers.items()):
    _kept = [entry for entry in _resolvers if entry[0] != _BOOL_TAG]
    if _kept:
        PlainBooleanLoader.yaml_implicit_resolvers[_letter] = _kept
    else:
        del PlainBooleanLoader.yaml_implicit_resolvers[_letter]

PlainBooleanLoader.add_implicit_resolver(_BOOL_TAG, _TRUE_FALSE, list("tTfF"))


class FrontMatterParser:
    """Split front matter text into fields and body text."""

    def parse(self, text: str) -> FrontMatter:
        lines = text.splitlines(keepends=True)
        self._require_open_marker(lines)
        close = self._find_close(lines)
        raw = "".join(lines[1:close])
        body = "".join(lines[close + 1:])
        return FrontMatter(fields=self._load_fields(raw), body=body)

    # The parser sees text only, so its errors carry an empty path.
    # The repository owns the file path and attaches it to every error.
    def _require_open_marker(self, lines: list[str]) -> None:
        if not lines or lines[0].strip() != _MARKER:
            raise BoardError(Path(""), "file has no front matter")

    def _find_close(self, lines: list[str]) -> int:
        for index in range(1, len(lines)):
            if lines[index].strip() == _MARKER:
                return index
        raise BoardError(Path(""), "front matter is not closed")

    def _load_fields(self, raw: str) -> Mapping[str, object]:
        try:
            data = yaml.load(raw, Loader=PlainBooleanLoader)
        except yaml.YAMLError as exc:
            raise BoardError(Path(""), f"bad YAML: {exc}") from exc
        if not isinstance(data, dict):
            raise BoardError(Path(""), "front matter is not a mapping")
        return MappingProxyType(data)
