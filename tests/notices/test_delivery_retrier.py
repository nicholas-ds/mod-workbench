"""Tests for DeliveryRetrier."""

from __future__ import annotations

import asyncio
import pytest

from workbench.notices.delivery_retrier import DeliveryRetrier
from workbench.notices.notice_types import DeliveryRecord, DeliveryState
from workbench.notices.owner_id import OwnerId

def _record(notice_id: str) -> DeliveryRecord:
    return DeliveryRecord(notice_id=notice_id, owner=OwnerId.parse("steam:123"),
                          state=DeliveryState.PENDING, attempts=0, last_try="", error="")

class FakeInbox:
    """Inbox fake: fails once on pending(), then returns canned records."""

    def __init__(self, records: list[DeliveryRecord],
                 fail_first_call: bool = False) -> None:
        self._records, self.calls = records, 0
        self._fail_first_call = fail_first_call

    def pending(self) -> list[DeliveryRecord]:
        self.calls += 1
        if self._fail_first_call and self.calls == 1:
            raise RuntimeError("boom")
        return list(self._records)

class FakeDispatcher:
    """Dispatcher fake that records every redeliver call."""

    def __init__(self) -> None:
        self.redelivered: list[DeliveryRecord] = []

    def redeliver(self, record: DeliveryRecord) -> DeliveryRecord:
        self.redelivered.append(record)
        return record

class FakeSleep:
    """Sleep fake: ends the loop with CancelledError on its second call."""

    def __init__(self) -> None:
        self.calls, self.seconds = 0, 0.0

    async def __call__(self, seconds: float) -> None:
        self.calls += 1
        self.seconds = seconds
        if self.calls >= 2:
            raise asyncio.CancelledError()

def test_retry_once_redelivers_every_pending_record() -> None:
    inbox = FakeInbox([_record("n1"), _record("n2")])
    dispatcher = FakeDispatcher()
    retrier = DeliveryRetrier(inbox, dispatcher, FakeSleep())

    assert retrier.retry_once() == 2
    assert [r.notice_id for r in dispatcher.redelivered] == ["n1", "n2"]

def test_run_survives_a_failing_pass_until_sleep_cancels() -> None:
    inbox, sleep = FakeInbox([], fail_first_call=True), FakeSleep()
    retrier = DeliveryRetrier(inbox, FakeDispatcher(), sleep, interval_seconds=5.0)

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(retrier.run())

    assert inbox.calls == 2 and sleep.calls == 2 and sleep.seconds == 5.0
