"""Abstract recipient that delivers notices to an owner."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from workbench.notices.owner_id import OwnerKind, OwnerId
from workbench.notices.notice_types import DeliveryState, Notice, Route


@dataclass(frozen=True)
class RecipientTraits:
    """Static facts about one recipient kind."""

    kind: OwnerKind
    label: str
    measures_context: bool
    fresh_mode: str
    retry_limit: int

    def as_json(self) -> dict[str, object]:
        return {
            "kind": self.kind.value,
            "label": self.label,
            "measures_context": self.measures_context,
            "fresh_mode": self.fresh_mode,
            "retry_limit": self.retry_limit,
        }


@dataclass(frozen=True)
class DeliveryOutcome:
    """Result of one deliver call."""

    state: DeliveryState
    error: str


class Recipient(ABC):
    """Deliver notices to one kind of owner."""

    @property
    @abstractmethod
    def traits(self) -> RecipientTraits:
        """Describe this recipient kind."""

    @abstractmethod
    def is_reachable(self, owner: OwnerId) -> bool:
        """Return True when the owner can receive lines."""

    @abstractmethod
    def context_percent(self, owner: OwnerId) -> float | None:
        """Return the owner's context usage percent, None when unknown."""

    @abstractmethod
    def send_line(self, owner: OwnerId, line: str) -> bool:
        """Send one line to the owner."""

    @abstractmethod
    def start_fresh(self, owner: OwnerId, prompt: str) -> bool:
        """Start a fresh context and seed it with the prompt."""

    def deliver(self, notice: Notice, route: Route,
                fresh_prompt: str) -> DeliveryOutcome:
        """Deliver one notice on the given route."""
        if not self.is_reachable(notice.owner):
            return DeliveryOutcome(state=DeliveryState.FAILED,
                                   error="owner not reachable")
        if route is Route.SEND:
            if self.send_line(notice.owner, notice.line):
                return DeliveryOutcome(state=DeliveryState.DELIVERED,
                                       error="")
            return DeliveryOutcome(state=DeliveryState.FAILED,
                                   error="send failed")
        if self.start_fresh(notice.owner, fresh_prompt):
            return DeliveryOutcome(state=DeliveryState.FRESH_STARTED,
                                   error="")
        return DeliveryOutcome(state=DeliveryState.FAILED,
                               error="fresh start failed")
