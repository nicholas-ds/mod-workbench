"""Tests for the orchestrator entry directory."""

from pathlib import Path

from workbench.core.config import ModConfig, ModError
from workbench.chat.orchestrator_directory import OrchestratorDirectory, OrchestratorEntry


def make_config(name: str, repo: Path) -> ModConfig:
    return ModConfig(
        name=name,
        repo=repo,
        platform=repo,
        screens=(),
        boards=repo / "boards",
        status=repo / "status.toml",
        tracking=repo / "tracking.md",
        log=repo / "LOG.md",
        briefs=repo / "briefs",
        exports=repo / "exports",
    )


class FakeRegistry:
    def __init__(self, results: list[ModConfig | ModError]) -> None:
        self._results = results

    def all(self) -> list[ModConfig | ModError]:
        return self._results


def make_directory(
    results: list[ModConfig | ModError],
    platform_folder: Path,
) -> OrchestratorDirectory:
    return OrchestratorDirectory(FakeRegistry(results), platform_folder)


def test_main_comes_first_with_platform_folder() -> None:
    directory = make_directory([], Path("E:/repos/mods/workbench"))
    assert directory.entries() == (
        OrchestratorEntry(name="main", folder="E:/repos/mods/workbench"),
    )


def test_each_mod_becomes_an_entry() -> None:
    results = [
        make_config("alpha", Path("E:/repos/mods/alpha")),
        make_config("beta", Path("E:/repos/mods/beta")),
    ]
    directory = make_directory(results, Path("E:/repos/mods/workbench"))
    assert directory.entries() == (
        OrchestratorEntry(name="main", folder="E:/repos/mods/workbench"),
        OrchestratorEntry(name="alpha", folder="E:/repos/mods/alpha"),
        OrchestratorEntry(name="beta", folder="E:/repos/mods/beta"),
    )


def test_mod_errors_are_skipped() -> None:
    results: list[ModConfig | ModError] = [
        ModError(repo=Path("E:/repos/mods/broken"), reason="no workbench.toml"),
        make_config("good", Path("E:/repos/mods/good")),
    ]
    directory = make_directory(results, Path("E:/repos/mods/workbench"))
    assert [entry.name for entry in directory.entries()] == ["main", "good"]


def test_folder_of_known_name() -> None:
    results = [make_config("alpha", Path("E:/repos/mods/alpha"))]
    directory = make_directory(results, Path("E:/repos/mods/workbench"))
    assert directory.folder_of("alpha") == "E:/repos/mods/alpha"


def test_folder_of_unknown_name_is_empty() -> None:
    directory = make_directory([], Path("E:/repos/mods/workbench"))
    assert directory.folder_of("nope") == ""


def test_folder_of_thread_name_resolves_to_orchestrator_folder() -> None:
    results = [make_config("alpha", Path("E:/repos/mods/alpha"))]
    directory = make_directory(results, Path("E:/repos/mods/workbench"))
    assert directory.folder_of("alpha~t2") == "E:/repos/mods/alpha"


def test_folder_of_unknown_orchestrator_with_thread_is_empty() -> None:
    directory = make_directory([], Path("E:/repos/mods/workbench"))
    assert directory.folder_of("nope~t1") == ""


def test_folder_of_bare_thread_id_is_empty() -> None:
    results = [make_config("alpha", Path("E:/repos/mods/alpha"))]
    directory = make_directory(results, Path("E:/repos/mods/workbench"))
    assert directory.folder_of("~t1") == ""
