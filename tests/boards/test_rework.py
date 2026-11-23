"""Tests for the rework brief writer."""

from pathlib import Path

from workbench.boards.board_types import Answer, Board, BoardEntry, Question
from workbench.core.config import ModConfig
from workbench.boards.rework import LogAppender, ReworkBriefWriter


def make_config(tmp_path: Path) -> ModConfig:
    repo = tmp_path / "repo"
    repo.mkdir()
    return ModConfig(
        name="Sample Mod",
        repo=repo,
        platform=repo / "platform",
        screens=("talent",),
        boards=repo / "boards",
        status=repo / "status",
        tracking=repo / "tracking.md",
        log=repo / "LOG.md",
        briefs=repo / "briefs",
        exports=repo / "exports",
    )


def make_question(qid: str, default: str, affects: tuple[str, ...]) -> Question:
    return Question(id=qid, type="choice", prompt=f"{qid}?", default=default, affects=affects)


def make_entry(*questions: Question, answers: tuple[Answer, ...] = ()) -> BoardEntry:
    board = Board(id="board-1", folder=Path("boards/open/board-1"), title="Layout",
                  questions=questions)
    return BoardEntry(board=board, answers=answers)


def test_all_defaults_writes_nothing(tmp_path: Path) -> None:
    cfg = make_config(tmp_path)
    entry = make_entry(
        make_question("layout", "compact", ("ui/queue.md",)),
        make_question("bars", "top", ("ui/bars.md",)),
        make_question("names", "on", ("ui/names.md",)),
        answers=(
            Answer(question_id="layout", picked="compact"),
            Answer(question_id="bars", picked="top"),
        ),
    )
    returned = ReworkBriefWriter(LogAppender()).write(cfg, entry)
    assert returned is None
    assert not cfg.briefs.exists()
    assert not cfg.log.exists()


def test_non_default_lists_affects(tmp_path: Path) -> None:
    cfg = make_config(tmp_path)
    entry = make_entry(
        make_question("layout", "compact", ("ui/queue.md", "ui/bars.md")),
        make_question("bars", "top", ("ui/score.md",)),
        answers=(
            Answer(question_id="layout", picked="wide"),
            Answer(question_id="bars", picked="top"),
        ),
    )
    brief_path = ReworkBriefWriter(LogAppender()).write(cfg, entry)
    assert brief_path == cfg.briefs / "rework-board-1.md"
    text = brief_path.read_text(encoding="utf-8")
    assert "board-1" in text
    assert "Picked: wide" in text
    assert "Default: compact" in text
    assert "- ui/queue.md" in text
    assert "- ui/bars.md" in text
    assert "ui/score.md" not in text


def test_log_line_appended(tmp_path: Path) -> None:
    cfg = make_config(tmp_path)
    cfg.log.write_text("older line\n", encoding="utf-8")
    entry = make_entry(
        make_question("layout", "compact", ("ui/queue.md",)),
        answers=(Answer(question_id="layout", picked="wide"),),
    )
    ReworkBriefWriter(LogAppender()).write(cfg, entry)
    lines = cfg.log.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "older line"
    assert len(lines) == 2
    assert "board-1" in lines[1]
    assert "rework-board-1.md" in lines[1]
