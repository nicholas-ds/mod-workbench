"""Tests for BoardOwnerStore: read and write-once semantics."""

from pathlib import Path

from workbench.notices.board_owner_store import BoardOwnerStore
from workbench.notices.owner_id import OwnerId, OwnerKind


def test_read_returns_stamped_owner(tmp_path: Path) -> None:
    store = BoardOwnerStore()
    store.write_once(tmp_path, OwnerId(OwnerKind.PANE, "boards-1"))

    assert store.read(tmp_path) == OwnerId(OwnerKind.PANE, "boards-1")


def test_read_returns_none_when_file_missing(tmp_path: Path) -> None:
    assert BoardOwnerStore().read(tmp_path / "open" / "b1") is None


def test_read_returns_none_when_file_invalid(tmp_path: Path) -> None:
    (tmp_path / "owner.json").write_text("{not json", encoding="utf-8")

    assert BoardOwnerStore().read(tmp_path) is None


def test_write_once_writes_owner_json_without_temp_leftover(tmp_path: Path) -> None:
    store = BoardOwnerStore()

    assert store.write_once(tmp_path, OwnerId(OwnerKind.CHAT, "review")) is True
    assert (tmp_path / "owner.json").exists()
    assert not (tmp_path / "owner.tmp").exists()


def test_store_never_overwrites_existing_stamp(tmp_path: Path) -> None:
    store = BoardOwnerStore()
    first = OwnerId(OwnerKind.PANE, "boards-1")
    second = OwnerId(OwnerKind.PANE, "boards-2")
    store.write_once(tmp_path, first)

    assert store.write_once(tmp_path, second) is False

    assert store.read(tmp_path) == first
