import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from notice_prompt import NoticePromptParser


def test_notice_line_returns_board_and_event() -> None:
    assert NoticePromptParser().parse(
        "[workbench] board=board-x event=closed.") == "board-x closed"


def test_normal_sentence_returns_none() -> None:
    assert NoticePromptParser().parse(
        "please fix the failing tests in main.py") is None


def test_leading_space_still_parses() -> None:
    assert NoticePromptParser().parse(
        "  [workbench] board=board-x event=closed.") == "board-x closed"
