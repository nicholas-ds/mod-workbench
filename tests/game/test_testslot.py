"""Tests for the test slot backup and restore."""

from pathlib import Path

import pytest

from scripts.restore_test_slot import RestoreCli
from workbench.game.testslot import (
    DirSnapshotter,
    FileHasher,
    MainSaveVerifier,
    SaveBackupService,
    SnapshotComparer,
    SlotConfig,
    SlotConfigLoader,
    SlotError,
    TestSlotRestorer,
)

QUICKSAVE = "Quicksave.0.sfs"
OTHER_SAVE = "autosave.sfs"
NOW = "20261107-120000"


def make_config(tmp_path: Path, **overrides: object) -> SlotConfig:
    baseline = tmp_path / "baseline.sfs"
    baseline.write_bytes(b"baseline-data")
    saves = tmp_path / "Saves"
    saves.mkdir()
    (saves / QUICKSAVE).write_bytes(b"old-quicksave")
    (saves / OTHER_SAVE).write_bytes(b"autosave-data")
    values: dict[str, object] = {
        "baseline": baseline,
        "baseline_sha256": FileHasher().sha256(baseline),
        "saves_dir": saves,
        "quicksave_name": QUICKSAVE,
        "backups_dir": tmp_path / "backups",
        "keep": 5,
    }
    values.update(overrides)
    return SlotConfig(**values)


def make_restorer() -> TestSlotRestorer:
    snapshotter = DirSnapshotter()
    verifier = MainSaveVerifier(snapshotter, SnapshotComparer())
    return TestSlotRestorer(FileHasher(), snapshotter, SaveBackupService(), verifier)


def folder_snapshot(saves: Path) -> dict[str, tuple[int, int]]:
    return dict(DirSnapshotter().snapshot(saves, frozenset()))


def write_cli_config(path: Path, baseline_sha256: str) -> None:
    lines = [
        'baseline = "baseline.sfs"',
        f'baseline_sha256 = "{baseline_sha256}"',
        'saves_dir = "Saves"',
        f'quicksave_name = "{QUICKSAVE}"',
        'backups_dir = "backups"',
        "keep = 5",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def make_cli(config_path: Path) -> RestoreCli:
    return RestoreCli(
        config_path=config_path,
        loader=SlotConfigLoader(),
        restorer=make_restorer(),
    )


def test_wrong_baseline_hash_changes_nothing(tmp_path: Path) -> None:
    cfg = make_config(tmp_path, baseline_sha256="0" * 64)
    before = folder_snapshot(cfg.saves_dir)
    with pytest.raises(SlotError):
        make_restorer().restore(cfg, NOW)
    assert folder_snapshot(cfg.saves_dir) == before
    assert not cfg.backups_dir.exists()


def test_missing_baseline_changes_nothing(tmp_path: Path) -> None:
    cfg = make_config(tmp_path, baseline=tmp_path / "gone.sfs")
    before = folder_snapshot(cfg.saves_dir)
    with pytest.raises(SlotError):
        make_restorer().restore(cfg, NOW)
    assert folder_snapshot(cfg.saves_dir) == before
    assert not cfg.backups_dir.exists()


def test_restore_writes_baseline_bytes_to_quicksave(tmp_path: Path) -> None:
    cfg = make_config(tmp_path)
    actions = make_restorer().restore(cfg, NOW)
    assert (cfg.saves_dir / QUICKSAVE).read_bytes() == b"baseline-data"
    assert (cfg.saves_dir / OTHER_SAVE).read_bytes() == b"autosave-data"
    assert len(actions) == 4


def test_backup_taken_before_overwrite(tmp_path: Path) -> None:
    cfg = make_config(tmp_path)
    make_restorer().restore(cfg, NOW)
    backup_quicksave = cfg.backups_dir / NOW / QUICKSAVE
    assert backup_quicksave.read_bytes() == b"old-quicksave"


def test_keeps_only_last_five_backups(tmp_path: Path) -> None:
    cfg = make_config(tmp_path)
    service = SaveBackupService()
    for index in range(7):
        service.backup(cfg, f"20261107-1200{index:02d}")
    names = sorted(p.name for p in cfg.backups_dir.iterdir())
    assert len(names) == 5
    assert names[0] == "20261107-120002"
    assert names[-1] == "20261107-120006"


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    cfg = make_config(tmp_path)
    before = folder_snapshot(cfg.saves_dir)
    actions = make_restorer().restore(cfg, NOW, dry_run=True)
    assert folder_snapshot(cfg.saves_dir) == before
    assert (cfg.saves_dir / QUICKSAVE).read_bytes() == b"old-quicksave"
    assert not cfg.backups_dir.exists()
    assert all("would" in action for action in actions[1:])


def test_restore_rejects_change_to_other_file(tmp_path: Path) -> None:
    cfg = make_config(tmp_path)

    class TamperingBackupService:
        def backup(self, cfg: SlotConfig, now: str) -> Path:
            (cfg.saves_dir / OTHER_SAVE).write_bytes(b"tampered")
            return SaveBackupService().backup(cfg, now)

    snapshotter = DirSnapshotter()
    verifier = MainSaveVerifier(snapshotter, SnapshotComparer())
    restorer = TestSlotRestorer(FileHasher(), snapshotter, TamperingBackupService(), verifier)
    with pytest.raises(SlotError):
        restorer.restore(cfg, NOW)


def test_verify_detects_changed_other_file(tmp_path: Path) -> None:
    cfg = make_config(tmp_path)
    before = DirSnapshotter().snapshot(cfg.saves_dir, frozenset((QUICKSAVE,)))
    (cfg.saves_dir / OTHER_SAVE).write_bytes(b"changed")
    with pytest.raises(SlotError):
        MainSaveVerifier(DirSnapshotter(), SnapshotComparer()).verify(cfg, before)


def test_verify_passes_when_only_quicksave_changed(tmp_path: Path) -> None:
    cfg = make_config(tmp_path)
    before = DirSnapshotter().snapshot(cfg.saves_dir, frozenset((QUICKSAVE,)))
    (cfg.saves_dir / QUICKSAVE).write_bytes(b"new-quicksave")
    MainSaveVerifier(DirSnapshotter(), SnapshotComparer()).verify(cfg, before)


def test_loader_reads_all_fields(tmp_path: Path) -> None:
    cfg_files = make_config(tmp_path)
    config_path = tmp_path / "testing.toml"
    write_cli_config(config_path, cfg_files.baseline_sha256)
    cfg = SlotConfigLoader().load(config_path)
    assert cfg.baseline == tmp_path / "baseline.sfs"
    assert cfg.baseline_sha256 == cfg_files.baseline_sha256
    assert cfg.saves_dir == tmp_path / "Saves"
    assert cfg.quicksave_name == QUICKSAVE
    assert cfg.backups_dir == tmp_path / "backups"
    assert cfg.keep == 5


def test_loader_rejects_missing_field(tmp_path: Path) -> None:
    config_path = tmp_path / "testing.toml"
    config_path.write_text('baseline = "b.sfs"\n', encoding="utf-8")
    with pytest.raises(SlotError):
        SlotConfigLoader().load(config_path)


def test_cli_exit_code_1_with_reason_on_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    cfg = make_config(tmp_path)
    (tmp_path / "baseline.sfs").unlink()
    config_path = tmp_path / "testing.toml"
    write_cli_config(config_path, cfg.baseline_sha256)
    code = make_cli(config_path).run([])
    out = capsys.readouterr().out
    assert code == 1
    assert len(out.strip().splitlines()) == 1
    assert "baseline" in out


def test_cli_success_returns_zero(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    cfg = make_config(tmp_path)
    config_path = tmp_path / "testing.toml"
    write_cli_config(config_path, cfg.baseline_sha256)
    code = make_cli(config_path).run([])
    out = capsys.readouterr().out
    assert code == 0
    assert (cfg.saves_dir / QUICKSAVE).read_bytes() == b"baseline-data"
    assert len(list(cfg.backups_dir.iterdir())) == 1
    assert "wrote baseline to" in out
