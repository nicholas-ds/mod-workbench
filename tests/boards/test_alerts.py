"""Tests for alert rules, report inspection, tracking and toasts."""

import logging
from pathlib import Path

import pytest

from workbench.boards.alerts import (
    AlertRules,
    NewBoardTracker,
    PermissionWaitAlert,
    ReportInspector,
    ToastNotifier,
)
from workbench.boards.board_types import Answer, Board, BoardEntry, Question


def make_entry(board_id: str, blocking: bool, answered: bool = False) -> BoardEntry:
    questions = (Question(id="q1", type="choice", prompt="Q?", blocking=blocking),)
    answers = (Answer(question_id="q1"),) if answered else ()
    board = Board(id=board_id, folder=Path(f"boards/open/{board_id}"),
                  title=board_id, questions=questions)
    return BoardEntry(board=board, answers=answers)


def test_only_blocking_alerts() -> None:
    rules = AlertRules()
    assert rules.should_alert(make_entry("b1", blocking=True))
    assert not rules.should_alert(make_entry("b2", blocking=False))
    assert not rules.should_alert(make_entry("b3", blocking=True, answered=True))


def test_tracker_returns_each_board_once() -> None:
    tracker = NewBoardTracker()
    entries = [make_entry("b1", True), make_entry("b2", True), make_entry("b3", False)]
    first = tracker.new_blocking(entries)
    second = tracker.new_blocking(entries + [make_entry("b4", True)])
    assert [entry.board.id for entry in first] == ["b1", "b2"]
    assert [entry.board.id for entry in second] == ["b4"]


def test_report_failed_true_for_fail_false_for_pass(tmp_path: Path) -> None:
    fail = tmp_path / "fail.md"
    fail.write_text("---\nresult: fail\n---\nbody\n", encoding="utf-8")
    passed = tmp_path / "pass.md"
    passed.write_text("---\nresult: pass\n---\nbody\n", encoding="utf-8")
    inspector = ReportInspector()
    assert inspector.has_failed(fail)
    assert not inspector.has_failed(passed)


def test_missing_toast_service_logs_and_does_not_raise(
    caplog: pytest.LogCaptureFixture,
) -> None:
    notifier = ToastNotifier(None)
    with caplog.at_level(logging.WARNING, logger="workbench.boards.alerts"):
        notifier.notify("title", "message")
    assert "toast" in caplog.text


def test_failing_toast_is_swallowed() -> None:
    class BrokenService:
        def send(self, title: str, message: str) -> None:
            raise RuntimeError("no toast service")

    ToastNotifier(source=BrokenService()).notify("title", "message")


def test_permission_wait_alert_sends_title_and_message() -> None:
    sent: list[tuple[str, str]] = []

    class FakeService:
        def send(self, title: str, message: str) -> None:
            sent.append((title, message))

    PermissionWaitAlert(ToastNotifier(FakeService())).notify("main", "Write")
    assert sent == [("Workbench: permission needed", "main waits to use Write")]
