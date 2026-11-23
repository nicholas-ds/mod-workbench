"""Tests for `TaskOverviewReader`: parse the master tracking file."""

from datetime import date
from pathlib import Path

from workbench.mods.task_overview import TaskOverviewReader

TODAY = date(2026, 11, 8)


def write_master(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "tracking.md"
    path.write_text(text, encoding="utf-8")
    return path


def test_parses_items_and_done_flag(tmp_path: Path) -> None:
    path = write_master(tmp_path,
                        "## CityMod\nupdated: 2026-11-08\n"
                        "- [ ] open task\n- [x] done task\n")
    repo = TaskOverviewReader().read(path, TODAY, ("CityMod",)).repos[0]
    assert repo.mod == "CityMod"
    assert repo.updated == "2026-11-08"
    assert [(item.text, item.done) for item in repo.items] == [
        ("open task", False), ("done task", True)]
    assert repo.open_count == 1
    assert repo.warning is None


def test_ignores_text_before_first_section(tmp_path: Path) -> None:
    path = write_master(tmp_path,
                        "# Master list\n- [ ] not a task\n\n"
                        "## CityMod\nupdated: 2026-11-08\n")
    overview = TaskOverviewReader().read(path, TODAY, ("CityMod",))
    assert len(overview.repos) == 1
    assert overview.repos[0].items == ()


def test_waits_marker_sets_flag_case_insensitive(tmp_path: Path) -> None:
    path = write_master(tmp_path,
                        "## CityMod\nupdated: 2026-11-08\n"
                        "- [ ] blocked task WAITS: AUTHOR\n- [ ] plain task\n")
    items = TaskOverviewReader().read(path, TODAY, ()).repos[0].items
    assert items[0].waits_for_author is True
    assert "WAITS: AUTHOR" in items[0].text
    assert items[1].waits_for_author is False


def test_missing_updated_gives_warning(tmp_path: Path) -> None:
    path = write_master(tmp_path, "## CityMod\n- [ ] open task\n")
    repo = TaskOverviewReader().read(path, TODAY, ()).repos[0]
    assert repo.updated is None
    assert repo.warning == "no updated date"


def test_bad_updated_gives_warning(tmp_path: Path) -> None:
    path = write_master(tmp_path, "## CityMod\nupdated: Nov 8 2026\n")
    repo = TaskOverviewReader().read(path, TODAY, ()).repos[0]
    assert repo.warning == "no updated date"


def test_old_updated_gives_stale_warning(tmp_path: Path) -> None:
    path = write_master(tmp_path, "## CityMod\nupdated: 2026-11-03\n")
    repo = TaskOverviewReader().read(path, TODAY, ()).repos[0]
    assert repo.warning == "stale: updated 5 days ago"


def test_known_mod_without_section_gives_warning(tmp_path: Path) -> None:
    path = write_master(tmp_path, "## CityMod\nupdated: 2026-11-08\n")
    overview = TaskOverviewReader().read(path, TODAY, ("CityMod", "HudMod"))
    assert overview.warnings == ("HudMod: no section in tracking.md",)


def test_missing_file_gives_not_found_warning(tmp_path: Path) -> None:
    overview = TaskOverviewReader().read(tmp_path / "tracking.md", TODAY, ("CityMod",))
    assert overview.repos == ()
    assert overview.warnings == ("tracking.md not found",)


def test_open_wait_item_without_board_id_warns(tmp_path) -> None:
    lines = ["## M", "updated: 2026-11-08", "- [ ] a. waits: author",
             "- [ ] b. waits: author, board: x", "- [x] c. waits: author"]
    path = tmp_path / "tracking.md"
    path.write_text(chr(10).join(lines), encoding="utf-8")
    overview = TaskOverviewReader().read(path, TODAY, ("M",))
    assert len(overview.warnings) == 1
    assert "a. waits" in overview.warnings[0]
