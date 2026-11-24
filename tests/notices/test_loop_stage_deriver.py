"""Tests for LoopStageDeriver."""

from __future__ import annotations

from datetime import datetime, timezone

from workbench.notices.loop_stage_deriver import LoopStageDeriver
from workbench.notices.loop_types import LoopInputs, LoopSnapshot, LoopStage, OwnerSignal, StallLimits
from workbench.notices.notice_types import DeliveryRecord, DeliveryState, Notice
from workbench.notices.owner_id import OwnerId, OwnerKind

NOW = datetime(2026, 11, 24, 12, 0, 0, tzinfo=timezone.utc)


def _record(state: DeliveryState, last_try: str = "2026-11-24T10:00:00") -> DeliveryRecord:
    return DeliveryRecord(notice_id="n1", owner=OwnerId(OwnerKind.PANE, "boards-1"),
                          state=state, attempts=2, last_try=last_try, error="")


def _notice() -> Notice:
    return Notice(id="n1", owner=OwnerId(OwnerKind.PANE, "boards-1"), board="storehouse",
                  event="changed", file_path="a.md", line="3", created="2026-11-24T09:00:00")


def _signal(**fields: str) -> OwnerSignal:
    values = {"prompt_notice": "storehouse changed", "prompt_at": "2026-11-24T11:45:00",
              "activity": "working", "activity_at": "2026-11-24T11:46:00"}
    values.update(fields)
    return OwnerSignal(**values)


def _derive(state: DeliveryState, signal: OwnerSignal | None = None,
            last_try: str = "2026-11-24T10:00:00", new_board_since: bool = False) -> LoopSnapshot:
    inputs = LoopInputs(record=_record(state, last_try), notice=_notice(), signal=signal,
                        new_board_since=new_board_since, now=NOW)
    return LoopStageDeriver(StallLimits()).derive(inputs)


def test_failed_record_is_stuck_and_can_retry() -> None:
    snap = _derive(DeliveryState.FAILED)

    assert snap.stage is LoopStage.STUCK
    assert snap.reason == "Not delivered"
    assert snap.can_retry is True
    assert snap.since == "2026-11-24T10:00:00"
    assert snap.notice_id == "n1"
    assert snap.board == "storehouse"
    assert snap.owner == "pane:boards-1"


def test_pending_unclaimed_stays_sending() -> None:
    snap = _derive(DeliveryState.PENDING)

    assert snap.stage is LoopStage.SENDING
    assert snap.reason == ""
    assert snap.can_retry is False
    assert snap.since == "2026-11-24T10:00:00"


def test_delivered_not_seen_in_time_is_stuck() -> None:
    snap = _derive(DeliveryState.DELIVERED, last_try="2026-11-24T11:55:00")

    assert snap.stage is LoopStage.STUCK
    assert snap.reason == "Not seen"
    assert snap.can_retry is False


def test_fresh_start_under_the_limit_stays_sending() -> None:
    snap = _derive(DeliveryState.FRESH_STARTED, last_try="2026-11-24T11:58:00")

    assert snap.stage is LoopStage.SENDING


def test_taken_needs_you_is_stuck() -> None:
    snap = _derive(DeliveryState.DELIVERED,
                   _signal(activity="needs-you", activity_at="2026-11-24T11:52:00"))

    assert snap.stage is LoopStage.STUCK
    assert snap.reason == "Waits for you"
    assert snap.since == "2026-11-24T11:52:00"


def test_taken_working_with_tool_call_is_working_else_got_it() -> None:
    snap = _derive(DeliveryState.DELIVERED,
                   _signal(last_tool="read", last_tool_at="2026-11-24T11:55:00"))

    assert snap.stage is LoopStage.WORKING
    assert snap.last_action == "read"
    assert snap.since == "2026-11-24T11:55:00"

    fresh = _derive(DeliveryState.DELIVERED, _signal(last_tool="", last_tool_at=""))
    assert fresh.stage is LoopStage.GOT_IT
    assert fresh.since == "2026-11-24T11:45:00"


def test_taken_working_but_quiet_is_stuck() -> None:
    snap = _derive(DeliveryState.DELIVERED,
                   _signal(prompt_at="2026-11-24T11:45:00",
                           last_tool="read", last_tool_at="2026-11-24T11:49:00"))

    assert snap.stage is LoopStage.STUCK
    assert snap.reason == "Quiet"


def test_taken_idle_finishing_is_done_else_stuck() -> None:
    done = _derive(DeliveryState.DELIVERED, _signal(activity="idle", phase="finished",
                                                    summary="fixed the board"))
    assert done.stage is LoopStage.DONE
    assert done.summary == "fixed the board"

    via_board = _derive(DeliveryState.DELIVERED, _signal(activity="idle"), new_board_since=True)
    assert via_board.stage is LoopStage.DONE

    stuck = _derive(DeliveryState.DELIVERED, _signal(activity="idle"))
    assert stuck.stage is LoopStage.STUCK
    assert stuck.reason == "Idle, no reply"
