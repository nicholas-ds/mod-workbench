"""Tests for the archive report writer (board archive step 5, revision 1)."""

from pathlib import Path

from workbench.archive.archive_report_writer import ArchiveReportWriter
from workbench.archive.archive_types import BoardArchiveResult


def _result(
    board_dir: Path = Path("done/b1"),
    file_count: int = 2,
    total_bytes: int = 4096,
    archived: bool = False,
    error: str = "",
) -> BoardArchiveResult:
    return BoardArchiveResult(
        board_dir=board_dir,
        file_count=file_count,
        total_bytes=total_bytes,
        archived=archived,
        error=error,
    )


def test_size_formatting() -> None:
    writer = ArchiveReportWriter()
    assert writer._format_size(512) == "512.0 B"
    assert writer._format_size(2048) == "2.0 KB"
    assert writer._format_size(3 * 1024 * 1024) == "3.0 MB"


def test_dry_run_lines() -> None:
    report = ArchiveReportWriter().write((_result(),), apply=False)
    lines = report.splitlines()
    assert lines[0] == "Archive (dry run, nothing written)"
    assert lines[1] == "b1: 2 files, 4.0 KB"
    assert lines[-1] == "Total: 1 boards, 4.0 KB"


def test_applied_line_says_zipped() -> None:
    result = _result(total_bytes=1024 * 1024, archived=True)
    report = ArchiveReportWriter().write((result,), apply=True)
    lines = report.splitlines()
    assert lines[0] == "Archive (applied)"
    assert lines[1] == "b1: 2 files, 1.0 MB zipped"
    assert lines[-1] == "Total: 1 boards, 1.0 MB"


def test_dry_run_never_says_zipped() -> None:
    result = _result(archived=True)
    report = ArchiveReportWriter().write((result,), apply=False)
    assert "zipped" not in report


def test_empty_results_give_nothing_to_archive() -> None:
    dry = ArchiveReportWriter().write((), apply=False)
    assert dry == "Archive (dry run, nothing written)\nNothing to archive."
    applied = ArchiveReportWriter().write((), apply=True)
    assert applied == "Archive (applied)\nNothing to archive."


def test_error_line_and_total_excludes_errors() -> None:
    ok = _result(board_dir=Path("done/b2"), archived=True)
    bad = _result(error="zip already exists")
    report = ArchiveReportWriter().write((bad, ok), apply=True)
    lines = report.splitlines()
    assert lines[1] == "b1: 2 files, 4.0 KB"
    assert lines[2] == "  error: b1: zip already exists"
    assert lines[3] == "b2: 2 files, 4.0 KB zipped"
    assert lines[-1] == "Total: 1 boards, 4.0 KB"


def test_only_errors_give_zero_total() -> None:
    report = ArchiveReportWriter().write((_result(error="verify failed"),), apply=True)
    assert report.splitlines()[-1] == "Total: 0 boards, 0.0 B"
