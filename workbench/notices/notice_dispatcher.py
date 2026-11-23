"""The delivery pipeline: resolve owner, compose notice, write, deliver."""

from __future__ import annotations

from collections.abc import Callable

from workbench.boards.board_types import Board
from workbench.notices.context_policy import ContextPolicy
from workbench.notices.fresh_start_prompt import FreshStartPrompt
from workbench.notices.notice_composer import NoticeComposer
from workbench.notices.notice_types import DeliveryRecord, DeliveryState, Notice
from workbench.notices.owner_id import OwnerId
from workbench.notices.owner_inbox import OwnerInbox
from workbench.notices.owner_resolver import OwnerResolver
from workbench.notices.recipient_resolver import RecipientResolver


class NoticeDispatcher:
    """Run one board event through the delivery pipeline."""

    def __init__(self, owner_resolver: OwnerResolver, composer: NoticeComposer,
                 inbox: OwnerInbox, recipient_resolver: RecipientResolver,
                 context_policy: ContextPolicy, fresh_prompt: FreshStartPrompt,
                 handoff_text_of: Callable[[OwnerId], str | None],
                 new_id: Callable[[], str], now: Callable[[], str]) -> None:
        self._owner_resolver = owner_resolver
        self._composer = composer
        self._inbox = inbox
        self._recipient_resolver = recipient_resolver
        self._context_policy = context_policy
        self._fresh_prompt = fresh_prompt
        self._handoff_text_of = handoff_text_of
        self._new_id = new_id
        self._now = now

    def dispatch(self, board: Board, event: str, file_path: str) -> DeliveryRecord:
        """Deliver a fresh notice for one board event."""
        resolution = self._owner_resolver.resolve(board)
        notice = self._composer.compose(self._new_id(), event, board.id,
                                        resolution.owner, file_path, self._now())
        record = self._inbox.write(notice, resolution.known)
        return self._deliver(notice, record, resolution.known)

    def redeliver(self, record: DeliveryRecord) -> DeliveryRecord:
        """Deliver again unless the notice is gone or the retry limit is hit."""
        notice = self._inbox.notice_of(record)
        if notice is None:
            return record
        recipient = self._recipient_resolver.resolve(record.owner)
        if record.attempts >= recipient.traits.retry_limit:
            return record
        return self._deliver(notice, record,
                             record.state != DeliveryState.UNKNOWN_OWNER)

    def _deliver(self, notice: Notice, record: DeliveryRecord,
                 known: bool) -> DeliveryRecord:
        """One delivery attempt; an unknown owner keeps its UNKNOWN_OWNER state."""
        recipient = self._recipient_resolver.resolve(notice.owner)
        percent = recipient.context_percent(notice.owner)
        route = self._context_policy.route(percent)
        prompt = self._fresh_prompt.build(self._handoff_text_of(notice.owner), notice)
        outcome = recipient.deliver(notice, route, prompt)
        state = outcome.state
        if not known and outcome.state in (DeliveryState.DELIVERED,
                                           DeliveryState.FRESH_STARTED):
            state = DeliveryState.UNKNOWN_OWNER
        updated = DeliveryRecord(notice_id=record.notice_id, owner=record.owner,
                                 state=state, attempts=record.attempts + 1,
                                 last_try=self._now(), error=outcome.error)
        self._inbox.update(updated)
        return updated
