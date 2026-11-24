"""Tests for OwnerResolver: store stamp, then raised_by, then fallback."""

from pathlib import Path

from workbench.boards.board_types import Board
from workbench.notices.board_owner_store import BoardOwnerStore
from workbench.notices.owner_id import OwnerId, OwnerKind
from workbench.notices.owner_resolver import OwnerResolution, OwnerResolver

_FALLBACK = OwnerId(OwnerKind.REPO, "StarfieldLogistics")


def _always(owner: OwnerId) -> bool:
    return True


def _board(folder: Path, raised_by: str | None) -> Board:
    return Board(id="b1", folder=folder, title="t", raised_by=raised_by)


def test_resolve_prefers_the_store_stamp(tmp_path: Path) -> None:
    store = BoardOwnerStore()
    store.write_once(tmp_path, OwnerId(OwnerKind.CHAT, "review"))
    resolver = OwnerResolver(store, _FALLBACK, _always)

    resolution = resolver.resolve(_board(tmp_path, "chat-other"))

    assert resolution == OwnerResolution(OwnerId(OwnerKind.CHAT, "review"), True)


def test_raised_by_chat_value_resolves_to_chat(tmp_path: Path) -> None:
    resolver = OwnerResolver(BoardOwnerStore(), _FALLBACK, _always)

    resolution = resolver.resolve(_board(tmp_path, "chat-review"))

    assert resolution == OwnerResolution(OwnerId(OwnerKind.CHAT, "review"), True)


def test_raised_by_pane_value_resolves_to_pane(tmp_path: Path) -> None:
    resolver = OwnerResolver(BoardOwnerStore(), _FALLBACK, _always)

    resolution = resolver.resolve(_board(tmp_path, "orchestrator~t1"))

    assert resolution == OwnerResolution(OwnerId(OwnerKind.PANE, "orchestrator~t1"), True)


def test_resolver_falls_back_with_known_false_when_raised_by_missing(tmp_path: Path) -> None:
    resolver = OwnerResolver(BoardOwnerStore(), _FALLBACK, _always)

    assert resolver.resolve(_board(tmp_path, None)) == OwnerResolution(_FALLBACK, False)
    assert resolver.resolve(_board(tmp_path, "")) == OwnerResolution(_FALLBACK, False)


def test_gone_owner_resolves_to_a_new_session_in_the_repo(tmp_path: Path) -> None:
    resolver = OwnerResolver(BoardOwnerStore(), _FALLBACK, lambda owner: False)

    resolution = resolver.resolve(_board(tmp_path, "chat-review"))

    assert resolution == OwnerResolution(_FALLBACK, False)
