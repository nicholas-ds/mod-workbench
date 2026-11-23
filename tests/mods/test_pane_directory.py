"""Tests: the pane directory lists every pane the author can target."""

from pathlib import Path

from api_fixtures import make_mod_repo, make_other_repo
from workbench.boards.answer_store import AnswerStore
from workbench.boards.board_builder import BoardBuilder
from workbench.boards.board_repository import BoardRepository
from workbench.core.config import ModConfigLoader, ModDiscovery
from workbench.boards.front_matter import FrontMatterParser
from workbench.mods.mod_registry import ModRegistry
from workbench.mods.pane_directory import PaneDirectory


def make_registry(root: Path) -> ModRegistry:
    return ModRegistry(ModDiscovery(ModConfigLoader()), [root],
                       BoardRepository(FrontMatterParser(), BoardBuilder()),
                       AnswerStore())


def test_list_all_lists_orchestrator_first_then_mod_panes(tmp_path: Path) -> None:
    make_mod_repo(tmp_path)
    make_other_repo(tmp_path)
    (tmp_path / "status").mkdir()
    (tmp_path / "status" / "main-orchestrator.toml").write_text(
        'wmux_surface = "surf-0"\n', encoding="utf-8")
    other_status = tmp_path / "OtherMod" / "status"
    (other_status / "planner.toml").write_text('wmux_surface = "surf-1"\n',
                                               encoding="utf-8")
    (other_status / "notes.txt").write_text("x", encoding="utf-8")
    (other_status / "broken.toml").write_text("kind = 'pane'\n", encoding="utf-8")
    entries = PaneDirectory(make_registry(tmp_path), tmp_path).list_all()
    assert [(entry.name, entry.mod, entry.pane.surface) for entry in entries] == [
        ("main-orchestrator", None, "surf-0"),
        ("planner", "OtherMod", "surf-1")]


def test_list_all_skips_mod_whose_status_is_a_file(tmp_path: Path) -> None:
    make_mod_repo(tmp_path)
    entries = PaneDirectory(make_registry(tmp_path), tmp_path).list_all()
    assert entries == ()


def test_find_returns_entry_by_name_and_none_for_unknown(tmp_path: Path) -> None:
    other_repo = make_other_repo(tmp_path)
    (other_repo / "status" / "planner.toml").write_text(
        'wmux_surface = "surf-1"\n', encoding="utf-8")
    directory = PaneDirectory(make_registry(tmp_path), tmp_path)
    entry = directory.find("planner")
    assert entry is not None
    assert entry.mod == "OtherMod"
    assert entry.repo == other_repo.resolve()
    assert directory.find("nope") is None


def test_list_all_drops_orchestrator_when_a_mod_pane_shares_its_surface(tmp_path: Path) -> None:
    make_mod_repo(tmp_path)
    make_other_repo(tmp_path)
    (tmp_path / "status").mkdir()
    (tmp_path / "status" / "main-orchestrator.toml").write_text(
        'wmux_surface = "surf-0"\n', encoding="utf-8")
    (tmp_path / "OtherMod" / "status" / "planner.toml").write_text(
        'wmux_surface = "surf-0"\n', encoding="utf-8")
    entries = PaneDirectory(make_registry(tmp_path), tmp_path).list_all()
    assert [entry.name for entry in entries] == ["planner"]


def test_entries_carry_their_status_file(tmp_path: Path) -> None:
    make_mod_repo(tmp_path)
    make_other_repo(tmp_path)
    (tmp_path / "status").mkdir()
    (tmp_path / "status" / "main-orchestrator.toml").write_text(
        'wmux_surface = "surf-0"\n', encoding="utf-8")
    (tmp_path / "OtherMod" / "status" / "planner.toml").write_text(
        'wmux_surface = "surf-1"\n', encoding="utf-8")
    entries = PaneDirectory(make_registry(tmp_path), tmp_path).list_all()
    assert [entry.status_file for entry in entries] == [
        tmp_path / "status" / "main-orchestrator.toml",
        tmp_path / "OtherMod" / "status" / "planner.toml"]
