"""Extract a one-line detail string from any backend's tool input."""

from __future__ import annotations

_TOOL_INPUT_KEYS = (
    "command",
    "file_path",
    "filePath",
    "path",
    "description",
    "pattern",
    "url",
)
_DETAIL_LIMIT = 100


def first_input_detail(tool_input: dict) -> str:
    for key in _TOOL_INPUT_KEYS:
        value = tool_input.get(key, "")
        if isinstance(value, str) and value.strip():
            one_line = " ".join(value.split())
            return one_line[:_DETAIL_LIMIT]
    return ""
