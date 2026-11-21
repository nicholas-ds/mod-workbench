"""Tests for the workbench command line: serve, init, check."""

from pathlib import Path

import pytest

from workbench.__main__ import DEFAULT_PORT, PortChooser, WorkbenchCommands, WorkbenchServer


def test_init_subcommand_creates_config_and_folders(tmp_path: Path,
                                                    capsys: pytest.CaptureFixture[str]) -> None:
    repo = tmp_path / "mod-a"
    repo.mkdir()

    code = WorkbenchCommands().run(["init", str(repo), "--name", "Mod A"])

    assert code == 0
    assert (repo / "workbench.toml").is_file()
    assert (repo / "boards" / "open").is_dir()
    assert "workbench.toml" in capsys.readouterr().out


def test_init_platform_option_reaches_config(tmp_path: Path) -> None:
    repo = tmp_path / "mod-a"
    platform = tmp_path / "the-platform"
    repo.mkdir()
    platform.mkdir()

    code = WorkbenchCommands().run(
        ["init", str(repo), "--name", "Mod A", "--platform", str(platform)]
    )

    assert code == 0
    text = (repo / "workbench.toml").read_text(encoding="utf-8")
    assert "the-platform" in text


def test_check_valid_board_exits_zero(tmp_path: Path) -> None:
    folder = tmp_path / "board-1"
    folder.mkdir()
    (folder / "board.md").write_text(
        "---\ntitle: T\nquestions: []\n---\n", encoding="utf-8"
    )

    assert WorkbenchCommands().run(["check", str(folder)]) == 0


def test_check_broken_board_exits_one_and_prints_lines(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    folder = tmp_path / "board-1"
    folder.mkdir()

    code = WorkbenchCommands().run(["check", str(folder)])

    assert code == 1
    assert "board.md" in capsys.readouterr().out


def test_serve_subcommand_runs_server(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WORKBENCH_PORT", raising=False)
    ports: list[int] = []
    monkeypatch.setattr(WorkbenchServer, "run", lambda self, port: ports.append(port))

    assert WorkbenchCommands().run(["serve"]) == 0
    assert WorkbenchCommands().run([]) == 0
    assert WorkbenchCommands().run(["serve", "--port", "9000"]) == 0
    assert ports == [DEFAULT_PORT, DEFAULT_PORT, 9000]


def test_port_flag_wins_over_env() -> None:
    assert PortChooser(DEFAULT_PORT).choose("9000", "7000") == 9000


def test_env_port_used_without_flag() -> None:
    assert PortChooser(DEFAULT_PORT).choose(None, "9000") == 9000


def test_default_port_matches_the_hooks_in_user_settings() -> None:
    assert PortChooser(DEFAULT_PORT).choose(None, None) == 8760


def test_bad_port_exits_2(capsys: pytest.CaptureFixture[str]) -> None:
    for raw in ["not-a-number", "0", "70000"]:
        code = WorkbenchCommands().run(["serve", "--port", raw])
        lines = capsys.readouterr().out.strip().splitlines()

        assert code == 2
        assert len(lines) == 1


def test_archive_on_empty_root_prints_nothing_to_archive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("WORKBENCH_ROOTS", str(tmp_path))

    assert WorkbenchCommands().run(["archive"]) == 0
    assert "Nothing to archive." in capsys.readouterr().out
