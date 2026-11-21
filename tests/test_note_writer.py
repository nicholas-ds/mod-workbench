"""Tests for the note writer."""

from pathlib import Path

from workbench.board_types import Board
from workbench.config import ModConfig
from workbench.front_matter import FrontMatterParser
from workbench.note_writer import NoteWriter

NOW = "2026-11-07T12:00:00"


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


def make_board() -> Board:
    return Board(id="board-1", folder=Path("boards/open/board-1"), title="Layout")


def test_note_file_has_coordinates(tmp_path: Path) -> None:
    cfg = make_config(tmp_path)
    note_path = NoteWriter().write(cfg, make_board(), "layout.png", 0.5, 0.25,
                                   "Move the counter", NOW)
    front_matter = FrontMatterParser().parse(note_path.read_text(encoding="utf-8"))
    assert front_matter.fields["board"] == "board-1"
    assert front_matter.fields["item"] == "layout.png"
    assert front_matter.fields["x"] == 0.5
    assert front_matter.fields["y"] == 0.25
    assert front_matter.fields["created"] == NOW
    assert "Move the counter" in front_matter.body


def test_note_numbers_increase(tmp_path: Path) -> None:
    cfg = make_config(tmp_path)
    board = make_board()
    writer = NoteWriter()
    first = writer.write(cfg, board, "layout.png", 0.1, 0.1, "one", NOW)
    second = writer.write(cfg, board, "layout.png", 0.2, 0.2, "two", NOW)
    assert first == cfg.repo / "notes" / "board-1-1.md"
    assert second == cfg.repo / "notes" / "board-1-2.md"
