"""Tests: PaneRegistry reads the orchestrator pane file."""

from pathlib import Path

from workbench.panes.pane_registry import OrchestratorPane, PaneRegistry


def test_find_returns_pane_from_file(tmp_path: Path) -> None:
    path = tmp_path / "main-orchestrator.toml"
    path.write_text('role = "main-orchestrator"\nwmux_surface = "surf-1"\n',
                    encoding="utf-8")
    assert PaneRegistry(path).find() == OrchestratorPane(surface="surf-1")


def test_find_returns_none_when_file_is_missing(tmp_path: Path) -> None:
    assert PaneRegistry(tmp_path / "missing.toml").find() is None


def test_find_returns_none_when_surface_key_is_missing(tmp_path: Path) -> None:
    path = tmp_path / "main-orchestrator.toml"
    path.write_text('role = "main-orchestrator"\n', encoding="utf-8")
    assert PaneRegistry(path).find() is None


def test_find_returns_none_when_file_is_not_toml(tmp_path: Path) -> None:
    path = tmp_path / "main-orchestrator.toml"
    path.write_text("not a toml file\n", encoding="utf-8")
    assert PaneRegistry(path).find() is None
