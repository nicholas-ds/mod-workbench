"""Normalize the server info command list for the chat slash picker (Task: slash skills).

The SDK's ``get_server_info()`` payload carries ``commands``: a list of
``{"name": ..., "description": ..., "argumentHint": ...}`` dicts, one per
skill, plugin command and builtin. The picker needs name and description only.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SlashCommandInfo:
    """One runnable chat command, as one row in the slash picker."""

    name: str
    description: str


class SlashCommandLister:
    """Extract sorted, de-duplicated command rows from a server info payload."""

    def list(
        self, server_info: dict[str, object] | None
    ) -> tuple[SlashCommandInfo, ...]:
        if not isinstance(server_info, dict):
            return ()
        commands = server_info.get("commands")
        if not isinstance(commands, list):
            return ()
        rows: dict[str, SlashCommandInfo] = {}
        for entry in commands:
            row = self._row_of(entry)
            if row is not None:
                rows.setdefault(row.name, row)
        return tuple(sorted(rows.values(), key=lambda row: row.name))

    def _row_of(self, entry: object) -> SlashCommandInfo | None:
        """One command dict as a row; odd entries give None."""
        if not isinstance(entry, dict):
            return None
        name = entry.get("name")
        if not isinstance(name, str) or not name:
            return None
        description = entry.get("description")
        if not isinstance(description, str):
            description = ""
        return SlashCommandInfo(name=name.lstrip("/"), description=description)
