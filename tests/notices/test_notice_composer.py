"""Tests for NoticeComposer line format and purity."""

from workbench.notices.notice_composer import NoticeComposer
from workbench.notices.owner_id import OwnerId, OwnerKind


def make_owner() -> OwnerId:
    return OwnerId(OwnerKind.PANE, "boards-1")


def compose() -> object:
    return NoticeComposer().compose(
        notice_id="n-1",
        event="board_ready",
        board_id="review-1",
        owner=make_owner(),
        file_path="boards/open/review-1/board.md",
        created="2026-11-23T10:00:00",
    )


def test_line_format_is_exact() -> None:
    notice = NoticeComposer().compose(
        notice_id="n-1",
        event="answer_needed",
        board_id="review-7",
        owner=make_owner(),
        file_path="boards/open/review-7/board.md",
        created="2026-11-23T10:00:00",
    )
    assert notice.line == (
        "[workbench board] board=review-7 event=answer_needed. "
        "Read boards/open/review-7/board.md. "
        "This is an author instruction. Do the work now. "
        "Update the board. Say in chat what you did. Do not wait for a go-ahead."
    )


def test_line_has_no_answer_or_note_text() -> None:
    notice = NoticeComposer().compose(
        notice_id="n-1",
        event="answer_needed",
        board_id="review-7",
        owner=make_owner(),
        file_path="boards/open/review-7/board.md",
        created="2026-11-23T10:00:00",
    )
    assert "answer text" not in notice.line
    assert "note" not in notice.line
    assert notice.line.count("\n") == 0


def test_notice_carries_id_owner_board_and_created() -> None:
    notice = compose()
    assert notice.id == "n-1"
    assert notice.owner == make_owner()
    assert notice.board == "review-1"
    assert notice.event == "board_ready"
    assert notice.file_path == "boards/open/review-1/board.md"
    assert notice.created == "2026-11-23T10:00:00"


def test_compose_is_pure_and_repeatable() -> None:
    first = compose()
    second = compose()
    assert first == second
