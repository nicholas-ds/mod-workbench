import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from pane_name_finder import PaneNameFinder

GLOB_PATTERNS = ("*/status/*.toml", "*/status/workspaces/*.toml")


def make_root(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "status").mkdir(parents=True)
    (repo / "status" / "pane-a.toml").write_text(
        'wmux_surface = "s1"\n', encoding="utf-8")
    (repo / "status" / "workspaces").mkdir()
    (repo / "status" / "workspaces" / "ws.toml").write_text(
        'wmux_surface = "s2"\n', encoding="utf-8")
    return tmp_path


def test_finder_returns_the_stem_of_the_surface_file(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    assert PaneNameFinder(root, GLOB_PATTERNS).name_of("s1") == "pane-a"
    assert PaneNameFinder(root, GLOB_PATTERNS).name_of("s2") == "ws"


def test_finder_returns_none_for_an_unknown_surface(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    assert PaneNameFinder(root, GLOB_PATTERNS).name_of("nope") is None


def test_finder_returns_the_first_file_when_two_declare_the_surface(
        tmp_path: Path) -> None:
    root = make_root(tmp_path)
    (root / "repo" / "status" / "aaa.toml").write_text(
        'wmux_surface = "s1"\n', encoding="utf-8")
    assert PaneNameFinder(root, GLOB_PATTERNS).name_of("s1") == "aaa"


def test_finder_skips_a_file_it_cannot_read(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    (root / "repo" / "status" / "locked.toml").mkdir()
    assert PaneNameFinder(root, GLOB_PATTERNS).name_of("s1") == "pane-a"


def test_finder_finds_files_in_other_repos_under_the_root(tmp_path: Path) -> None:
    root = make_root(tmp_path)
    other = root / "other-repo" / "status"
    other.mkdir(parents=True)
    (other / "pane-b.toml").write_text('wmux_surface = "s3"\n', encoding="utf-8")
    assert PaneNameFinder(root, GLOB_PATTERNS).name_of("s3") == "pane-b"
