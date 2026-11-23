"""Tests for FreshStartPrompt assembly."""

from workbench.notices.fresh_start_prompt import FreshStartPrompt
from workbench.notices.notice_types import Notice
from workbench.notices.owner_id import OwnerId, OwnerKind


def make_notice(line: str = "[workbench] board=review-1 event=answer_needed. Read b.md.") -> Notice:
    return Notice(
        id="n-1",
        owner=OwnerId(OwnerKind.PANE, "boards-1"),
        board="review-1",
        event="answer_needed",
        file_path="b.md",
        line=line,
        created="2026-11-23T10:00:00",
    )


def test_first_line_announces_fresh_session() -> None:
    prompt = FreshStartPrompt().build("Continue here.", make_notice())
    assert prompt.splitlines()[0] == "Fresh session started by the workbench."


def test_none_handoff_becomes_missing_file_line() -> None:
    prompt = FreshStartPrompt().build(None, make_notice())
    lines = prompt.splitlines()
    assert "Handoff from the previous session:" in lines
    assert "No handoff file was found." in lines
    assert lines.index("No handoff file was found.") > lines.index(
        "Handoff from the previous session:"
    )


def test_handoff_text_is_included_under_heading() -> None:
    prompt = FreshStartPrompt().build("Finish the export work.", make_notice())
    lines = prompt.splitlines()
    assert "Finish the export work." in lines
    assert lines.index("Finish the export work.") == lines.index(
        "Handoff from the previous session:"
    ) + 1


def test_notice_line_is_last() -> None:
    notice = make_notice()
    prompt = FreshStartPrompt().build("Handoff body.", notice)
    assert prompt.splitlines()[-1] == notice.line
