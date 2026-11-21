"""Generic table construction from records."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class Table:
    columns: tuple[str, ...]
    rows: tuple[Mapping[str, object], ...]


class TableBuilder:
    """Builds one table whose columns are the union of record keys."""

    def build(self, records: list[Mapping[str, object]]) -> Table:
        columns = self._collect_columns(records)
        rows = tuple(self._fill_row(record, columns) for record in records)
        return Table(columns=columns, rows=rows)

    def _collect_columns(
        self, records: list[Mapping[str, object]]
    ) -> tuple[str, ...]:
        seen: dict[str, None] = {}
        for record in records:
            for key in record:
                seen.setdefault(key, None)
        return tuple(seen)

    def _fill_row(
        self, record: Mapping[str, object], columns: tuple[str, ...]
    ) -> dict[str, object]:
        return {column: record.get(column, "") for column in columns}
