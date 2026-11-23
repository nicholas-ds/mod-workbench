"""Text report for the done-board archive run.

Spec: board archive, revision 1. Pure formatting, no I/O.
"""

from __future__ import annotations

from workbench.archive.archive_types import BoardArchiveResult

KB = 1024
MB = 1024 * 1024


class ArchiveReportWriter:
    def write(self, results: tuple[BoardArchiveResult, ...], apply: bool) -> str:
        header = (
            "Archive (applied)" if apply else "Archive (dry run, nothing written)"
        )
        if not results:
            return "\n".join([header, "Nothing to archive."])
        lines: list[str] = [header]
        total_boards = 0
        total_bytes = 0
        for result in results:
            lines.append(self._board_line(result, apply))
            lines.extend(self._error_lines(result))
            if not result.error:
                total_boards += 1
                total_bytes += result.total_bytes
        lines.append(
            f"Total: {total_boards} boards, {self._format_size(total_bytes)}"
        )
        return "\n".join(lines)

    def _board_line(self, result: BoardArchiveResult, apply: bool) -> str:
        suffix = " zipped" if apply and result.archived else ""
        return (
            f"{result.board_dir.name}: {result.file_count} files,"
            f" {self._format_size(result.total_bytes)}{suffix}"
        )

    def _error_lines(self, result: BoardArchiveResult) -> list[str]:
        if not result.error:
            return []
        return [f"  error: {result.board_dir.name}: {result.error}"]

    def _format_size(self, size: int) -> str:
        if size >= MB:
            return f"{size / MB:.1f} MB"
        if size >= KB:
            return f"{size / KB:.1f} KB"
        return f"{size:.1f} B"
