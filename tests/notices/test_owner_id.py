"""Tests for OwnerId parsing and text round trips."""

from dataclasses import FrozenInstanceError

import pytest

from workbench.notices.owner_id import OwnerId, OwnerKind


def test_parse_reads_pane_prefix() -> None:
    owner = OwnerId.parse("pane:boards-1")
    assert owner == OwnerId(OwnerKind.PANE, "boards-1")


def test_parse_reads_chat_prefix() -> None:
    owner = OwnerId.parse("chat:review")
    assert owner == OwnerId(OwnerKind.CHAT, "review")


def test_parse_reads_old_chat_raised_by_value() -> None:
    owner = OwnerId.parse("chat-review")
    assert owner == OwnerId(OwnerKind.CHAT, "review")


def test_parse_treats_bare_text_as_pane_key() -> None:
    owner = OwnerId.parse("orchestrator~t1")
    assert owner == OwnerId(OwnerKind.PANE, "orchestrator~t1")


def test_parse_empty_text_raises() -> None:
    with pytest.raises(ValueError):
        OwnerId.parse("")


def test_text_round_trips_through_parse() -> None:
    owner = OwnerId(OwnerKind.CHAT, "review")
    assert owner.text() == "chat:review"
    assert OwnerId.parse(owner.text()) == owner


def test_owner_id_is_frozen() -> None:
    owner = OwnerId(OwnerKind.PANE, "boards-1")
    with pytest.raises(FrozenInstanceError):
        owner.key = "other"
