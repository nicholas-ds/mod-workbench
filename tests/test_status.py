from pathlib import Path

from workbench.status import Status, StatusReader, WorkerExtractor, WorkspaceStatus

STATUS_TOML = "\n".join(
    [
        "[workers.alloy]",
        'phase = "cast"',
        "count = 3",
        "",
        "[workers.smith]",
        'phase = "forge"',
        "count = 1",
    ]
)


def test_missing_file_gives_empty_dict(tmp_path: Path) -> None:
    status = StatusReader().read(tmp_path / "STATUS.toml")
    assert isinstance(status, Status)
    assert dict(status.values) == {}


def test_unknown_keys_kept(tmp_path: Path) -> None:
    path = tmp_path / "STATUS.toml"
    path.write_text('build = "v3"\n', encoding="utf-8")
    status = StatusReader().read(path)
    assert status.values["build"] == "v3"


def test_workers_lists_each_table_with_name(tmp_path: Path) -> None:
    path = tmp_path / "STATUS.toml"
    path.write_text(STATUS_TOML + "\n", encoding="utf-8")
    status = StatusReader().read(path)
    workers = WorkerExtractor().extract(status)
    assert [w.name for w in workers] == ["alloy", "smith"]
    assert workers[0].fields["phase"] == "cast"
    assert workers[1].fields["count"] == 1


def test_folder_gives_one_entry_per_toml_file(tmp_path: Path) -> None:
    (tmp_path / "alpha.toml").write_text('build = "a"\n', encoding="utf-8")
    (tmp_path / "beta.toml").write_text('build = "b"\n', encoding="utf-8")
    (tmp_path / "notes.txt").write_text("ignore me\n", encoding="utf-8")
    entries = StatusReader().read_all(tmp_path)
    assert [entry.workspace for entry in entries] == ["alpha", "beta"]
    assert entries[0].values["build"] == "a"
    assert entries[1].values["build"] == "b"


def test_single_file_gives_one_entry(tmp_path: Path) -> None:
    path = tmp_path / "main.toml"
    path.write_text('build = "v3"\n', encoding="utf-8")
    entries = StatusReader().read_all(path)
    assert len(entries) == 1
    assert isinstance(entries[0], WorkspaceStatus)
    assert entries[0].workspace == "main"
    assert entries[0].values["build"] == "v3"


def test_missing_path_gives_empty_tuple(tmp_path: Path) -> None:
    assert StatusReader().read_all(tmp_path / "nope") == ()


def test_bad_toml_file_is_skipped_with_error_key(tmp_path: Path) -> None:
    path = tmp_path / "broken.toml"
    path.write_text("key = [1, 2", encoding="utf-8")
    entries = StatusReader().read_all(path)
    assert len(entries) == 1
    assert entries[0].workspace == "broken"
    assert "error" in entries[0].values
    assert "build" not in entries[0].values
