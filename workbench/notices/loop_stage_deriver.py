"""Derives the loop stage of a notice from pure inputs, no I/O."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from workbench.notices.loop_types import LoopInputs, LoopSnapshot, LoopStage, StallLimits
from workbench.notices.notice_types import DeliveryState


@dataclass(frozen=True)
class _Outcome:
    """What one rule decided, before the snapshot is assembled."""

    stage: LoopStage
    reason: str = ""
    since: str = ""
    last_action: str = ""
    summary: str = ""
    can_retry: bool = False


class LoopStageDeriver:
    """Turns a delivery record, notice and owner signal into a loop snapshot."""

    def __init__(self, limits: StallLimits) -> None:
        self._limits = limits

    def derive(self, inputs: LoopInputs) -> LoopSnapshot:
        taken = self._taken(inputs)
        outcome = self._decide(inputs, taken)
        return LoopSnapshot(notice_id=inputs.record.notice_id, board=inputs.notice.board,
                            owner=inputs.record.owner.text(), stage=outcome.stage,
                            reason=outcome.reason, since=outcome.since,
                            last_action=outcome.last_action, summary=outcome.summary,
                            can_retry=outcome.can_retry)

    def _decide(self, inputs: LoopInputs, taken: bool) -> _Outcome:
        steps = (self._from_failed(inputs), self._from_pending(inputs, taken),
                 self._from_unseen(inputs, taken), self._from_needs_you(inputs, taken),
                 self._from_working(inputs, taken), self._from_idle(inputs, taken))
        for step in steps:
            if step is not None:
                return step
        return _Outcome(stage=LoopStage.SENDING)

    def _tag(self, inputs: LoopInputs) -> str:
        return f"{inputs.notice.board} {inputs.notice.event}"

    def _taken(self, inputs: LoopInputs) -> bool:
        signal = inputs.signal
        if signal is None or signal.prompt_notice != self._tag(inputs):
            return False
        prompt_at = self._parse(signal.prompt_at)
        last_try = self._parse(inputs.record.last_try)
        if prompt_at is None or last_try is None:
            return False
        return prompt_at >= last_try

    def _from_failed(self, inputs: LoopInputs) -> _Outcome | None:
        if inputs.record.state is not DeliveryState.FAILED:
            return None
        return _Outcome(stage=LoopStage.STUCK, reason="Not delivered",
                        since=inputs.record.last_try, can_retry=True)

    def _from_pending(self, inputs: LoopInputs, taken: bool) -> _Outcome | None:
        if taken or inputs.record.state is not DeliveryState.PENDING:
            return None
        return _Outcome(stage=LoopStage.SENDING, since=inputs.record.last_try)

    def _from_unseen(self, inputs: LoopInputs, taken: bool) -> _Outcome | None:
        unseen = (DeliveryState.DELIVERED, DeliveryState.FRESH_STARTED, DeliveryState.UNKNOWN_OWNER)
        if taken or inputs.record.state not in unseen:
            return None
        if self._age(inputs, inputs.record.last_try) > self._limits.not_seen_seconds:
            return _Outcome(stage=LoopStage.STUCK, reason="Not seen", since=inputs.record.last_try)
        return _Outcome(stage=LoopStage.SENDING, since=inputs.record.last_try)

    def _from_needs_you(self, inputs: LoopInputs, taken: bool) -> _Outcome | None:
        signal = inputs.signal
        if not taken or signal is None or signal.activity != "needs-you":
            return None
        return _Outcome(stage=LoopStage.STUCK, reason="Waits for you", since=signal.activity_at)

    def _from_working(self, inputs: LoopInputs, taken: bool) -> _Outcome | None:
        signal = inputs.signal
        if not taken or signal is None or signal.activity not in ("working", "worker"):
            return None
        tool_at = self._parse(signal.last_tool_at)
        prompt_at = self._parse(signal.prompt_at)
        if tool_at is None or prompt_at is None or tool_at <= prompt_at:
            return _Outcome(stage=LoopStage.GOT_IT, since=signal.prompt_at)
        if self._age(inputs, signal.last_tool_at) > self._limits.quiet_seconds:
            return _Outcome(stage=LoopStage.STUCK, reason="Quiet", since=signal.last_tool_at)
        return _Outcome(stage=LoopStage.WORKING, last_action=signal.last_tool,
                        since=signal.last_tool_at)

    def _from_idle(self, inputs: LoopInputs, taken: bool) -> _Outcome | None:
        signal = inputs.signal
        if not taken or signal is None or signal.activity != "idle":
            return None
        if signal.phase == "finished" or inputs.new_board_since:
            return _Outcome(stage=LoopStage.DONE, summary=signal.summary, since=signal.activity_at)
        return _Outcome(stage=LoopStage.STUCK, reason="Idle, no reply", since=signal.activity_at)

    def _parse(self, raw: str) -> datetime | None:
        try:
            moment = datetime.fromisoformat(raw)
        except (TypeError, ValueError):
            return None
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        return moment

    def _age(self, inputs: LoopInputs, raw: str) -> float:
        moment = self._parse(raw)
        if moment is None:
            return 0.0
        return (inputs.now - moment).total_seconds()
