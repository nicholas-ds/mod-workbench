"""Tests for RecipientResolver."""

import pytest

from workbench.notices.owner_id import OwnerId, OwnerKind
from workbench.notices.recipient import Recipient, RecipientTraits
from workbench.notices.recipient_resolver import RecipientResolver, UnknownRecipientError


class FakeRecipient(Recipient):
    """Recipient stub that only carries traits."""

    def __init__(self, traits: RecipientTraits) -> None:
        self._traits = traits

    @property
    def traits(self) -> RecipientTraits:
        return self._traits

    def is_reachable(self, owner: OwnerId) -> bool:
        return True

    def context_percent(self, owner: OwnerId) -> float | None:
        return None

    def send_line(self, owner: OwnerId, line: str) -> bool:
        return True

    def start_fresh(self, owner: OwnerId, prompt: str) -> bool:
        return True


def _traits(kind: OwnerKind) -> RecipientTraits:
    return RecipientTraits(kind, f"label-{kind.value}", False, "none", 1)


def resolver() -> tuple[RecipientResolver, FakeRecipient, FakeRecipient]:
    pane = FakeRecipient(_traits(OwnerKind.PANE))
    chat = FakeRecipient(_traits(OwnerKind.CHAT))
    return RecipientResolver({OwnerKind.PANE: pane, OwnerKind.CHAT: chat}), pane, chat


def test_resolve_picks_the_recipient_for_the_kind() -> None:
    obj, pane, chat = resolver()
    assert obj.resolve(OwnerId(OwnerKind.PANE, "main")) is pane
    assert obj.resolve(OwnerId(OwnerKind.CHAT, "review")) is chat


def test_resolve_raises_for_a_missing_kind() -> None:
    empty = RecipientResolver({})
    with pytest.raises(UnknownRecipientError):
        empty.resolve(OwnerId(OwnerKind.PANE, "main"))


def test_unknown_recipient_error_is_a_key_error() -> None:
    assert issubclass(UnknownRecipientError, KeyError)


def test_all_traits_lists_every_registered_recipient() -> None:
    obj, _pane, _chat = resolver()
    assert obj.all_traits() == (_traits(OwnerKind.PANE), _traits(OwnerKind.CHAT))
