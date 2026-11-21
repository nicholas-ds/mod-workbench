from pathlib import Path

import pytest

from workbench.config import (
    ConfigError,
    ModConfig,
    ModConfigLoader,
    ModDiscovery,
    ModError,
)

CONFIG_TOML = "\n".join(
    [
        'name = "Test Mod"',
        'platform = ".."',
        'screens = ["ui/**/*.swf"]',
        'boards = "boards"',
        'status = "STATUS.md"',
        'tracking = "tracking.md"',
        'log = "LOG.md"',
        'briefs = "briefs"',
        'exports = "exports"',
    ]
)


def make_repo(parent: Path, name: str, content: str = CONFIG_TOML) -> Path:
    repo = parent / name
    repo.mkdir()
    (repo / "workbench.toml").write_text(content + "\n", encoding="utf-8")
    return repo


def test_load_valid_config(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "mod-a")
    cfg = ModConfigLoader().load(repo)
    assert isinstance(cfg, ModConfig)
    assert cfg.name == "Test Mod"
    assert cfg.repo == repo
    assert cfg.boards == repo / "boards"
    assert cfg.platform == tmp_path
    assert cfg.screens == ("ui/**/*.swf",)
    for path in (cfg.repo, cfg.platform, cfg.boards, cfg.status, cfg.tracking,
                 cfg.log, cfg.briefs, cfg.exports):
        assert path.is_absolute()


def test_missing_name_raises(tmp_path: Path) -> None:
    repo = make_repo(tmp_path, "mod-b", 'platform = ".."\n')
    with pytest.raises(ConfigError):
        ModConfigLoader().load(repo)


def test_discover_returns_error_for_bad_repo(tmp_path: Path) -> None:
    make_repo(tmp_path, "good")
    make_repo(tmp_path, "bad", 'boards = "boards"\n')
    discovery = ModDiscovery(ModConfigLoader())
    results = discovery.discover([tmp_path])
    mods = [r for r in results if isinstance(r, ModConfig)]
    errors = [r for r in results if isinstance(r, ModError)]
    assert len(mods) == 1
    assert mods[0].name == "Test Mod"
    assert len(errors) == 1
    assert errors[0].repo == tmp_path / "bad"
