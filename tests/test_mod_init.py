"""Tests for ModInitializer."""

import os
from pathlib import Path

import pytest

from workbench.config import ModConfigLoader
from workbench.mod_init import ModInitializer


def test_init_creates_config_and_folders(tmp_path: Path) -> None:
    repo = tmp_path / "mod-a"
    repo.mkdir()
    platform = tmp_path / "platform"
    platform.mkdir()

    created = ModInitializer().init(repo, "Mod A", platform)

    config = repo / "workbench.toml"
    assert config.is_file()
    assert created == [
        config,
        repo / "boards" / "open",
        repo / "boards" / "done",
        repo / "status",
        repo / "notes",
    ]
    text = config.read_text(encoding="utf-8")
    assert 'name = "Mod A"' in text
    assert 'boards = "boards"' in text
    assert 'status = "status"' in text


def test_init_does_not_overwrite(tmp_path: Path) -> None:
    repo = tmp_path / "mod-a"
    repo.mkdir()
    config = repo / "workbench.toml"
    config.write_text("# keep me\n", encoding="utf-8")

    created = ModInitializer().init(repo, "Mod A", tmp_path)

    assert config.read_text(encoding="utf-8") == "# keep me\n"
    assert config not in created
    assert (repo / "boards" / "open").is_dir()
    assert (repo / "notes").is_dir()


def test_init_output_loads_with_mod_config_loader(tmp_path: Path) -> None:
    repo = tmp_path / "mod-a"
    repo.mkdir()
    platform = tmp_path / "platform"
    platform.mkdir()
    ModInitializer().init(repo, "Mod A", platform)

    cfg = ModConfigLoader().load(repo)

    assert cfg.name == "Mod A"
    assert cfg.platform == platform
    assert cfg.boards == (repo / "boards").resolve()
    assert cfg.status == (repo / "status").resolve()
    for path in (cfg.tracking, cfg.log, cfg.briefs, cfg.exports):
        assert path.is_absolute()


def _raise_cross_drive(target: str, start: str) -> str:
    raise ValueError(f"path is on mount '{target[:2]}', start on mount '{start[:2]}'")


def _cross_drive_platform(repo: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    repo_drive = repo.drive[:1].upper()
    for code in range(ord("A"), ord("Z") + 1):
        letter = chr(code)
        if letter == repo_drive:
            continue
        candidate = Path(f"{letter}:/platform")
        if candidate.drive and Path(candidate.anchor).exists():
            return candidate
    monkeypatch.setattr(os.path, "relpath", _raise_cross_drive)
    return Path("Q:/platform")


@pytest.mark.skipif(os.name != "nt", reason="cross-drive paths are a Windows case")
def test_cross_drive_platform_is_written_absolute(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "mod-a"
    repo.mkdir()
    platform = _cross_drive_platform(repo, monkeypatch)

    ModInitializer().init(repo, "Mod A", platform)

    text = (repo / "workbench.toml").read_text(encoding="utf-8")
    assert platform.is_absolute()
    assert f'platform = "{platform.as_posix()}"' in text


def test_same_drive_platform_stays_relative(tmp_path: Path) -> None:
    repo = tmp_path / "mod-a"
    repo.mkdir()
    platform = tmp_path / "platform"
    platform.mkdir()

    ModInitializer().init(repo, "Mod A", platform)

    text = (repo / "workbench.toml").read_text(encoding="utf-8")
    expected = Path(os.path.relpath(platform, repo)).as_posix()
    assert f'platform = "{expected}"' in text


@pytest.mark.skipif(os.name != "nt", reason="cross-drive paths are a Windows case")
def test_loader_resolves_absolute_platform_to_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "mod-a"
    repo.mkdir()
    platform = _cross_drive_platform(repo, monkeypatch)
    ModInitializer().init(repo, "Mod A", platform)

    cfg = ModConfigLoader().load(repo)

    assert cfg.platform == platform.resolve()
