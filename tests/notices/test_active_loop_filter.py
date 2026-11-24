"""Tests for the active loop snapshot filter."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from workbench.notices.active_loop_filter import ActiveLoopFilter
from workbench.notices.loop_types import LoopSnapshot, LoopStage

NOW = datetime(2026, 11, 24, 12, 0, 0, tzinfo=timezone.utc)


def snapshot(stage: LoopStage, since: str, notice_id: str = "n1") -> LoopSnapshot:
    return LoopSnapshot(notice_id=notice_id, board="b", owner="o", stage=stage,
                        reason="r", since=since, last_action="a", summary="s",
                        can_retry=False)


def iso_before(minutes: int) -> str:
    return (NOW - timedelta(minutes=minutes)).isoformat()


def test_keeps_done_five_minutes_old() -> None:
    kept = ActiveLoopFilter().select(
        [snapshot(LoopStage.DONE, iso_before(5))], NOW)
    assert len(kept) == 1


def test_drops_done_twenty_minutes_old() -> None:
    kept = ActiveLoopFilter().select(
        [snapshot(LoopStage.DONE, iso_before(20))], NOW)
    assert kept == []


def test_drops_stuck_seven_hours_old() -> None:
    kept = ActiveLoopFilter().select(
        [snapshot(LoopStage.STUCK, iso_before(7 * 60))], NOW)
    assert kept == []


def test_drops_bad_since() -> None:
    kept = ActiveLoopFilter().select(
        [snapshot(LoopStage.WORKING, "not-a-time")], NOW)
    assert kept == []


def test_stuck_first_and_done_last() -> None:
    stages = [LoopStage.DONE, LoopStage.SENDING, LoopStage.GOT_IT,
              LoopStage.WORKING, LoopStage.STUCK]
    snapshots = [snapshot(stage, iso_before(1), f"n{index}")
                 for index, stage in enumerate(stages)]
    kept = ActiveLoopFilter().select(snapshots, NOW)
    assert [s.stage for s in kept] == [LoopStage.STUCK, LoopStage.WORKING,
                                       LoopStage.GOT_IT, LoopStage.SENDING,
                                       LoopStage.DONE]


def test_superseded_loop_is_dropped() -> None:
    moved_on = LoopSnapshot(notice_id="n1", board="b", owner="o", stage=LoopStage.DONE,
                            reason="Moved on", since=iso_before(1), last_action="",
                            summary="", can_retry=False)

    assert ActiveLoopFilter().select([moved_on], NOW) == []
