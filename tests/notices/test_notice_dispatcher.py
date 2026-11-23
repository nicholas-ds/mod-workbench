"""Tests for NoticeDispatcher: dispatch, redeliver and the unknown-owner rule."""

from pathlib import Path

from workbench.boards.board_types import Board
from workbench.notices.context_policy import ContextPolicy
from workbench.notices.fresh_start_prompt import FreshStartPrompt
from workbench.notices.notice_composer import NoticeComposer
from workbench.notices.notice_dispatcher import NoticeDispatcher
from workbench.notices.notice_types import DeliveryRecord, DeliveryState
from workbench.notices.owner_id import OwnerId, OwnerKind
from workbench.notices.owner_inbox import OwnerInbox
from workbench.notices.owner_resolver import OwnerResolution
from workbench.notices.recipient import Recipient, RecipientTraits
from workbench.notices.recipient_resolver import RecipientResolver

OWNER = OwnerId(OwnerKind.PANE, "boards-1")


class FakeOwnerResolver:
    def __init__(self, resolution: OwnerResolution) -> None:
        self._resolution = resolution

    def resolve(self, board: Board) -> OwnerResolution:
        return self._resolution


class FakeRecipient(Recipient):
    def __init__(self, traits: RecipientTraits, percent: float | None = None) -> None:
        self._traits = traits
        self._percent = percent
        self.sent: list[str] = []
        self.fresh_prompts: list[str] = []

    @property
    def traits(self) -> RecipientTraits:
        return self._traits

    def is_reachable(self, owner: OwnerId) -> bool:
        return True

    def context_percent(self, owner: OwnerId) -> float | None:
        return self._percent

    def send_line(self, owner: OwnerId, line: str) -> bool:
        self.sent.append(line)
        return True

    def start_fresh(self, owner: OwnerId, prompt: str) -> bool:
        self.fresh_prompts.append(prompt)
        return True


def _traits(retry_limit: int = 3) -> RecipientTraits:
    return RecipientTraits(kind=OwnerKind.PANE, label="pane", measures_context=True,
                           fresh_mode="clear", retry_limit=retry_limit)


def _dispatcher(tmp_path: Path, recipient: FakeRecipient, known: bool,
                percent: float | None = None) -> NoticeDispatcher:
    recipients = {OwnerKind.PANE: recipient, OwnerKind.CHAT: recipient}
    return NoticeDispatcher(
        owner_resolver=FakeOwnerResolver(OwnerResolution(OWNER, known)),
        composer=NoticeComposer(), inbox=OwnerInbox(tmp_path),
        recipient_resolver=RecipientResolver(recipients),
        context_policy=ContextPolicy(), fresh_prompt=FreshStartPrompt(),
        handoff_text_of=lambda owner: "handoff text", new_id=lambda: "n1",
        now=lambda: "2026-11-23T10:00:00")


def _board(tmp_path: Path) -> Board:
    return Board(id="b1", folder=tmp_path, title="t")


def test_dispatch_answer_reaches_pane(tmp_path: Path) -> None:
    recipient = FakeRecipient(_traits())
    dispatcher = _dispatcher(tmp_path, recipient, known=True)

    record = dispatcher.dispatch(_board(tmp_path), "answer", "boards/open/b1/board.md")

    assert len(recipient.sent) == 1
    assert "[workbench]" in recipient.sent[0]
    assert "boards/open/b1/board.md" in recipient.sent[0]
    assert record.state is DeliveryState.DELIVERED
    assert record.attempts == 1
    assert record.last_try == "2026-11-23T10:00:00"
    assert record.error == ""


def test_unknown_owner_stays_unknown_owner(tmp_path: Path) -> None:
    recipient = FakeRecipient(_traits())
    dispatcher = _dispatcher(tmp_path, recipient, known=False)

    record = dispatcher.dispatch(_board(tmp_path), "answer", "boards/open/b1/board.md")

    assert record.state is DeliveryState.UNKNOWN_OWNER
    assert record.error == ""
    assert record.attempts == 1


def test_above_25_percent_starts_fresh(tmp_path: Path) -> None:
    recipient = FakeRecipient(_traits(), percent=30.0)
    dispatcher = _dispatcher(tmp_path, recipient, known=True)

    record = dispatcher.dispatch(_board(tmp_path), "answer", "boards/open/b1/board.md")

    assert len(recipient.fresh_prompts) == 1
    assert "handoff text" in recipient.fresh_prompts[0]
    assert record.state is DeliveryState.FRESH_STARTED


def test_redeliver_stops_at_retry_limit(tmp_path: Path) -> None:
    recipient = FakeRecipient(_traits(retry_limit=1))
    dispatcher = _dispatcher(tmp_path, recipient, known=True)
    record = dispatcher.dispatch(_board(tmp_path), "answer", "boards/open/b1/board.md")

    again = dispatcher.redeliver(record)

    assert again == record
    assert again.attempts == 1
    assert len(recipient.sent) == 1


def test_redeliver_without_stored_notice_returns_record(tmp_path: Path) -> None:
    recipient = FakeRecipient(_traits())
    dispatcher = _dispatcher(tmp_path, recipient, known=True)
    ghost = DeliveryRecord(notice_id="ghost", owner=OWNER, state=DeliveryState.PENDING,
                           attempts=0, last_try="", error="")

    assert dispatcher.redeliver(ghost) is ghost
    assert recipient.sent == []
