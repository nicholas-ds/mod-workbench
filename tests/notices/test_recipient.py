"""Tests for the Recipient base class deliver logic."""

from workbench.notices.notice_types import DeliveryState, Notice, Route
from workbench.notices.owner_id import OwnerId, OwnerKind
from workbench.notices.recipient import Recipient, RecipientTraits


class FakeRecipient(Recipient):
    """Recipient stub with configurable answers."""

    def __init__(self, reachable: bool = True, send_ok: bool = True,
                 fresh_ok: bool = True) -> None:
        self.reachable = reachable
        self.send_ok = send_ok
        self.fresh_ok = fresh_ok
        self.sent: list[str] = []
        self.fresh_prompts: list[str] = []

    @property
    def traits(self) -> RecipientTraits:
        return RecipientTraits(OwnerKind.PANE, "fake", False, "none", 1)

    def is_reachable(self, owner: OwnerId) -> bool:
        return self.reachable

    def context_percent(self, owner: OwnerId) -> float | None:
        return None

    def send_line(self, owner: OwnerId, line: str) -> bool:
        self.sent.append(line)
        return self.send_ok

    def start_fresh(self, owner: OwnerId, prompt: str) -> bool:
        self.fresh_prompts.append(prompt)
        return self.fresh_ok


def notice() -> Notice:
    return Notice(id="n1", owner=OwnerId(kind=OwnerKind.PANE, key="main"),
                  board="boards/open/demo", event="question",
                  file_path="status/workspaces/workbench.toml",
                  line="[workbench] hello", created="2026-11-23T00:00:00")


def test_traits_as_json_uses_plain_values() -> None:
    traits = RecipientTraits(OwnerKind.PANE, "pane", True, "clear-pane", 5)
    assert traits.as_json() == {"kind": "pane", "label": "pane",
                                "measures_context": True,
                                "fresh_mode": "clear-pane", "retry_limit": 5}


def test_deliver_unreachable_owner_fails() -> None:
    recipient = FakeRecipient(reachable=False)
    outcome = recipient.deliver(notice(), Route.SEND, "fresh prompt")
    assert outcome.state is DeliveryState.FAILED
    assert outcome.error == "owner not reachable"
    assert recipient.sent == []


def test_deliver_send_success() -> None:
    recipient = FakeRecipient()
    outcome = recipient.deliver(notice(), Route.SEND, "fresh prompt")
    assert outcome.state is DeliveryState.DELIVERED
    assert outcome.error == ""
    assert recipient.sent == ["[workbench] hello"]


def test_deliver_send_failure() -> None:
    recipient = FakeRecipient(send_ok=False)
    outcome = recipient.deliver(notice(), Route.SEND, "fresh prompt")
    assert outcome.state is DeliveryState.FAILED
    assert outcome.error == "send failed"


def test_deliver_fresh_success() -> None:
    recipient = FakeRecipient()
    outcome = recipient.deliver(notice(), Route.FRESH, "fresh prompt")
    assert outcome.state is DeliveryState.FRESH_STARTED
    assert outcome.error == ""
    assert recipient.fresh_prompts == ["fresh prompt"]


def test_deliver_fresh_failure() -> None:
    recipient = FakeRecipient(fresh_ok=False)
    outcome = recipient.deliver(notice(), Route.FRESH, "fresh prompt")
    assert outcome.state is DeliveryState.FAILED
    assert outcome.error == "fresh start failed"
