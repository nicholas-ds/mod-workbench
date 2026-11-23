"""Board folders on disk: load one board, list boards by state."""

from __future__ import annotations

from pathlib import Path

from workbench.boards.board_builder import BoardBuilder
from workbench.boards.board_types import Board, BoardError, FrontMatter
from workbench.boards.front_matter import FrontMatterParser

OPEN_STATE = "open"
DONE_STATE = "done"
BOARD_FILE = "board.md"


class BoardRepository:
    """Read board.md files and list board folders in one state."""

    def __init__(self, parser: FrontMatterParser, builder: BoardBuilder) -> None:
        self._parser = parser
        self._builder = builder

    def load(self, folder: Path) -> Board:
        folder = Path(folder)
        text = self._read_text(folder)
        front_matter = self._parse(folder, text)
        return self._builder.build(folder, front_matter)

    def list_boards(self, boards_dir: Path, state: str) -> list[Board | BoardError]:
        if state not in (OPEN_STATE, DONE_STATE):
            raise ValueError(f"state must be open or done, got: {state}")
        state_dir = Path(boards_dir) / state
        if not state_dir.is_dir():
            return []
        return [self._load_one(folder) for folder in self._board_folders(state_dir)]

    def _board_folders(self, state_dir: Path) -> list[Path]:
        return sorted(path for path in state_dir.iterdir() if path.is_dir())

    def _read_text(self, folder: Path) -> str:
        try:
            return (folder / BOARD_FILE).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise BoardError(folder, f"cannot read {BOARD_FILE}: {exc}") from exc

    # The parser sees text only and raises BoardError with an empty path;
    # this call owns the folder path and attaches it to a BoardError.
    def _parse(self, folder: Path, text: str) -> FrontMatter:
        try:
            return self._parser.parse(text)
        except BoardError as exc:
            raise BoardError(folder, exc.reason) from exc

    def _load_one(self, folder: Path) -> Board | BoardError:
        try:
            return self.load(folder)
        except BoardError as exc:
            return exc
