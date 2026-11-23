"""Tests for QueueSorter and BlockingRule."""

from pathlib import Path

from workbench.boards.board_types import Answer, Board, BoardEntry, Question
from workbench.boards.queue import BlockingRule, QueueSorter

SORTER = QueueSorter()
RULE = BlockingRule()


def make_question(question_id: str, blocking: bool, affects: tuple[str, ...]) -> Question:
    return Question(id=question_id, type="choice", prompt="Q?",
                    blocking=blocking, affects=affects)


def make_entry(board_id: str, created: str, questions: tuple[Question, ...],
               answered_ids: tuple[str, ...] = ()) -> BoardEntry:
    answers = tuple(Answer(question_id=qid) for qid in answered_ids)
    board = Board(id=board_id, folder=Path(f"boards/open/{board_id}"),
                  title=board_id, created=created, questions=questions)
    return BoardEntry(board=board, answers=answers)


def test_rule_flags_unanswered_blocking() -> None:
    entry = make_entry("b1", "2026-11-07T10:00:00", (make_question("q1", True, ()),))
    assert RULE.is_blocking(entry)


def test_rule_clears_answered_blocking() -> None:
    entry = make_entry("b1", "2026-11-07T10:00:00",
                       (make_question("q1", True, ()),), ("q1",))
    assert not RULE.is_blocking(entry)


def test_unanswered_blocking_first() -> None:
    blocking = make_entry("blocking", "2026-11-07T10:00:00",
                          (make_question("q1", True, ()),))
    plain = make_entry("plain", "2026-11-01T09:00:00",
                       (make_question("q2", False, ("ui/a.md",)),))
    assert SORTER.sort([plain, blocking]) == [blocking, plain]


def test_answered_blocking_not_blocking() -> None:
    answered = make_entry("answered", "2026-11-07T10:00:00",
                          (make_question("q1", True, ()),), ("q1",))
    plain = make_entry("plain", "2026-11-01T09:00:00",
                       (make_question("q2", False, ()),))
    assert SORTER.sort([answered, plain]) == [plain, answered]


def test_more_affects_first() -> None:
    wide = make_entry("wide", "2026-11-07T10:00:00",
                      (make_question("q1", True, ("ui/a.md", "ui/b.md")),))
    narrow = make_entry("narrow", "2026-11-07T09:00:00",
                        (make_question("q1", True, ("ui/a.md",)),))
    assert SORTER.sort([narrow, wide]) == [wide, narrow]


def test_older_first() -> None:
    older = make_entry("older", "2026-11-01T09:00:00",
                       (make_question("q1", False, ("ui/a.md",)),))
    newer = make_entry("newer", "2026-11-07T10:00:00",
                       (make_question("q1", False, ("ui/a.md",)),))
    assert SORTER.sort([newer, older]) == [older, newer]
