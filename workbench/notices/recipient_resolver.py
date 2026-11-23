"""Pick the recipient that matches an owner's kind."""

from __future__ import annotations

from collections.abc import Mapping

from workbench.notices.owner_id import OwnerKind, OwnerId
from workbench.notices.recipient import Recipient, RecipientTraits


class UnknownRecipientError(KeyError):
    """Raised when no recipient is registered for an owner kind."""


class RecipientResolver:
    """The only place that picks a recipient by owner kind."""

    def __init__(self, recipients: Mapping[OwnerKind, Recipient]) -> None:
        self._recipients = dict(recipients)

    def resolve(self, owner: OwnerId) -> Recipient:
        """Return the recipient for the owner's kind."""
        recipient = self._recipients.get(owner.kind)
        if recipient is None:
            raise UnknownRecipientError(owner.kind.value)
        return recipient

    def all_traits(self) -> tuple[RecipientTraits, ...]:
        """Return the traits of every registered recipient."""
        return tuple(recipient.traits
                     for recipient in self._recipients.values())
