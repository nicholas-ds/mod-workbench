"""Tests: the handoff scanner lists research items that wait."""

from pathlib import Path

from workbench.core.config import ModConfig, ModError
from workbench.handoff.handoff_scanner import (
    BoardTextReader,
    HandoffScanner,
    OpenRequestReader,
    TrackingTextReader,
    UnpickedFileFinder,
)
from workbench.handoff.handoff_types import FILES_KIND, REQUESTS_KIND


class FakeRegistry:
    def __init__(self, results: list[ModConfig | ModError]) -> None:
        self._results = results

    def all(self) -> list[ModConfig | ModError]:
        return self._results


def make_cfg(repo: Path, name: str = "CityMod", tracking: Path | None = None) -> ModConfig:
    return ModConfig(name=name, repo=repo, platform=repo, screens=("ui/**/*.swf",),
                     boards=repo / "boards", status=repo, tracking=tracking or repo, log=repo,
                     briefs=repo, exports=repo)


def write_handoff(repo: Path, requests: str = "", files: dict[str, str] | None = None) -> Path:
    handoff = repo / "docs" / "research-handoff"
    handoff.mkdir(parents=True)
    (handoff / "README.md").write_text("how this folder works\n", encoding="utf-8")
    (handoff / "requests.md").write_text(requests, encoding="utf-8")
    for name, text in (files or {}).items():
        (handoff / name).write_text(text, encoding="utf-8")
    return handoff


# --- OpenRequestReader -------------------------------------------------------


def test_reader_returns_stripped_open_request_lines(tmp_path: Path) -> None:
    requests = tmp_path / "requests.md"
    requests.write_text("# requests\n\n- [open] how many cows? (needed for: barn)\n"
                        "  tail line kept with request\n", encoding="utf-8")
    lines = OpenRequestReader().read(requests)
    assert lines == ("- [open] how many cows? (needed for: barn)",)


def test_reader_ignores_answered_and_other_lines(tmp_path: Path) -> None:
    requests = tmp_path / "requests.md"
    requests.write_text("- [answered 2026-11-18] done question\n"
                        "- [open] live question\n"
                        "- plain bullet\n", encoding="utf-8")
    assert OpenRequestReader().read(requests) == ("- [open] live question",)


def test_reader_gives_empty_tuple_for_missing_file(tmp_path: Path) -> None:
    assert OpenRequestReader().read(tmp_path / "requests.md") == ()


# --- UnpickedFileFinder ------------------------------------------------------


def test_finder_lists_sorted_unpicked_names(tmp_path: Path) -> None:
    handoff = write_handoff(tmp_path, files={"zz-topic.md": "t", "aa-topic.md": "t"})
    assert UnpickedFileFinder().find(handoff, ()) == ("aa-topic.md", "zz-topic.md")


def test_finder_counts_file_named_in_a_board_as_picked(tmp_path: Path) -> None:
    handoff = write_handoff(tmp_path, files={"picked.md": "t", "unpicked.md": "t"})
    texts = ("see picked.md for the answer", "board.md body")
    assert UnpickedFileFinder().find(handoff, texts) == ("unpicked.md",)


def test_finder_ignores_readme_and_requests(tmp_path: Path) -> None:
    handoff = write_handoff(tmp_path)
    assert UnpickedFileFinder().find(handoff, ()) == ()


def test_finder_gives_empty_tuple_for_missing_dir(tmp_path: Path) -> None:
    assert UnpickedFileFinder().find(tmp_path / "none", ()) == ()


# --- BoardTextReader ---------------------------------------------------------


def test_reader_reads_board_and_item_files_under_open_and_done(tmp_path: Path) -> None:
    for state in ("open", "done"):
        folder = tmp_path / state / "b1"
        folder.mkdir(parents=True)
        (folder / "board.md").write_text(f"{state} board\n", encoding="utf-8")
        (folder / "01-item.html").write_text(f"<p>{state} item</p>\n", encoding="utf-8")
        (folder / "02-item.md").write_text(f"{state} note\n", encoding="utf-8")
        (folder / "03-shot.png").write_bytes(b"png")
    texts = BoardTextReader().read(tmp_path)
    assert sorted(texts) == ["<p>done item</p>\n", "<p>open item</p>\n",
                             "done board\n", "done note\n",
                             "open board\n", "open note\n"]


def test_reader_gives_empty_tuple_for_missing_dir(tmp_path: Path) -> None:
    assert BoardTextReader().read(tmp_path / "none") == ()


# --- TrackingTextReader ------------------------------------------------------


def test_tracking_reader_reads_the_file_text(tmp_path: Path) -> None:
    tracking = tmp_path / "tracking.md"
    tracking.write_text("done: topic.md\n", encoding="utf-8")
    assert TrackingTextReader().read(tracking) == ("done: topic.md\n",)


def test_tracking_reader_gives_empty_tuple_for_missing_file(tmp_path: Path) -> None:
    assert TrackingTextReader().read(tmp_path / "none.md") == ()


# --- HandoffScanner ----------------------------------------------------------


def test_scanner_report_is_empty_when_nothing_waits(tmp_path: Path) -> None:
    write_handoff(tmp_path, requests="- [answered] old question\n")
    registry = FakeRegistry([make_cfg(tmp_path)])
    report = scanner_for(registry).scan()
    assert report.rows == ()
    assert report.total == 0


def test_scanner_targets_request_row_at_research_mod_and_prefixes_items(tmp_path: Path) -> None:
    write_handoff(tmp_path, requests="- [open] how many cows?\n")
    registry = FakeRegistry([make_cfg(tmp_path)])
    report = scanner_for(registry).scan()
    assert len(report.rows) == 1
    row = report.rows[0]
    assert row.kind == REQUESTS_KIND
    assert row.target == "ResearchMod"
    assert row.label == "Research"
    assert row.items == ("CityMod: - [open] how many cows?",)
    assert report.total == 1


def test_scanner_lists_unpicked_files_per_mod_and_skips_picked(tmp_path: Path) -> None:
    write_handoff(tmp_path, files={"picked.md": "t", "waiting.md": "t"})
    boards = tmp_path / "boards" / "open" / "b1"
    boards.mkdir(parents=True)
    (boards / "board.md").write_text("answer in picked.md\n", encoding="utf-8")
    registry = FakeRegistry([make_cfg(tmp_path)])
    report = scanner_for(registry).scan()
    assert len(report.rows) == 1
    row = report.rows[0]
    assert row.kind == FILES_KIND
    assert row.target == "CityMod"
    assert row.label == "CityMod"
    assert row.items == ("waiting.md",)
    assert report.total == 1


def test_scanner_counts_file_named_only_in_tracking_as_picked(tmp_path: Path) -> None:
    write_handoff(tmp_path, files={"waiting.md": "t"})
    (tmp_path / "tracking.md").write_text("plan: see waiting.md\n", encoding="utf-8")
    registry = FakeRegistry([make_cfg(tmp_path, tracking=tmp_path / "tracking.md")])
    report = scanner_for(registry).scan()
    assert report.rows == ()
    assert report.total == 0


def test_scanner_keeps_file_listed_when_tracking_file_is_missing(tmp_path: Path) -> None:
    write_handoff(tmp_path, files={"waiting.md": "t"})
    registry = FakeRegistry([make_cfg(tmp_path, tracking=tmp_path / "none.md")])
    report = scanner_for(registry).scan()
    assert len(report.rows) == 1
    assert report.rows[0].items == ("waiting.md",)


def test_scanner_merges_requests_of_all_mods_and_skips_errors(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    write_handoff(first, requests="- [open] question one\n")
    write_handoff(second, requests="- [open] question two\n")
    bare = tmp_path / "bare"
    bare.mkdir()
    error = ModError(repo=tmp_path / "broken", reason="no workbench.toml")
    registry = FakeRegistry([make_cfg(first, "FirstMod"), make_cfg(bare, "BareMod"),
                             error, make_cfg(second, "SecondMod")])
    report = scanner_for(registry).scan()
    assert len(report.rows) == 1
    assert report.rows[0].items == ("FirstMod: - [open] question one",
                                    "SecondMod: - [open] question two")
    assert report.total == 2


def scanner_for(registry: FakeRegistry) -> HandoffScanner:
    return HandoffScanner(registry=registry, research_mod="ResearchMod",
                          request_reader=OpenRequestReader(),
                          file_finder=UnpickedFileFinder(),
                          board_reader=BoardTextReader(),
                          tracking_reader=TrackingTextReader())
