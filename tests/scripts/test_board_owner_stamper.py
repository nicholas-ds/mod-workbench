import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from board_owner_stamper import BoardOwnerStamper
from pane_name_finder import PaneNameFinder

GLOB_PATTERNS = ("*/status/*.toml", "*/status/workspaces/*.toml")


def make_root(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "status").mkdir(parents=True)
    (repo / "status" / "pane-a.toml").write_text(
        'wmux_surface = "s1"\n', encoding="utf-8")
    board = repo / "boards" / "open" / "b1"
    board.mkdir(parents=True)
    (board / "board.md").write_text("---\ntitle: b\n---\n", encoding="utf-8")
    return tmp_path


def make_stamper(root: Path) -> BoardOwnerStamper:
    return BoardOwnerStamper(PaneNameFinder(root, GLOB_PATTERNS))


def test_stamp_writes_the_owner_once(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    board_md = str(root / "repo" / "boards" / "open" / "b1" / "board.md")
    assert make_stamper(root).stamp(board_md, "s1") is True
    owner = root / "repo" / "boards" / "open" / "b1" / "owner.json"
    assert json.loads(owner.read_text(encoding="utf-8")) == {"owner": "pane:pane-a"}


def test_stamp_accepts_the_backslash_style(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    board_md = str(root / "repo" / "boards" / "open" / "b1" / "board.md")
    assert "\\" in board_md
    assert make_stamper(root).stamp(board_md.replace("/", "\\"), "s1") is True


def test_stamp_does_not_overwrite_an_existing_owner(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    board_md = str(root / "repo" / "boards" / "open" / "b1" / "board.md")
    owner = root / "repo" / "boards" / "open" / "b1" / "owner.json"
    owner.write_text('{"owner": "pane:first"}', encoding="utf-8")
    assert make_stamper(root).stamp(board_md, "s1") is False
    assert owner.read_text(encoding="utf-8") == '{"owner": "pane:first"}'


def test_stamp_ignores_files_outside_a_board_folder(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    other = str(root / "repo" / "status" / "pane-a.toml")
    assert make_stamper(root).stamp(other, "s1") is False
    assert not list(root.rglob("owner.json"))


def test_stamp_ignores_an_unknown_surface(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    board_md = str(root / "repo" / "boards" / "open" / "b1" / "board.md")
    assert make_stamper(root).stamp(board_md, "ghost") is False
    assert not list(root.rglob("owner.json"))


def test_stamp_returns_false_instead_of_raising_on_a_missing_folder(
        tmp_path: Path) -> None:
    root = make_root(tmp_path)
    board_md = str(root / "repo" / "boards" / "open" / "gone" / "board.md")
    assert make_stamper(root).stamp(board_md, "s1") is False


def test_stamp_chat_writes_a_chat_owner(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    board_md = str(root / "repo" / "boards" / "open" / "b1" / "board.md")
    assert make_stamper(root).stamp_chat(board_md, "review~t1") is True
    owner = root / "repo" / "boards" / "open" / "b1" / "owner.json"
    assert json.loads(owner.read_text(encoding="utf-8")) == {"owner": "chat:review~t1"}
