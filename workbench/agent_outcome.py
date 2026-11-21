"""Outcome labels for agent records: work that went nowhere, or is fine.

`AgentOutcomeClassifier` is pure: it takes an `AgentRecord` and a `now_ms`
timestamp and answers with an `AgentOutcome`. No clock, file or network
access, so the same inputs always give the same outcome.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from workbench.agent_event import STATE_FINISHED, STATE_RUNNING

if TYPE_CHECKING:
    from workbench.agent_registry import AgentRecord

_DROP_MINUTES = 10
_STALL_MINUTES = 15
_ABANDON_MINUTES = 60

DROP_LIMIT_MS = _DROP_MINUTES * 60 * 1000
STALL_LIMIT_MS = _STALL_MINUTES * 60 * 1000
ABANDON_LIMIT_MS = _ABANDON_MINUTES * 60 * 1000

DROPPED = "dropped"
STALLED = "stalled"
ABANDONED = "abandoned"
EMPTY = "empty"
OK = "ok"


@dataclass(frozen=True)
class AgentOutcome:
    label: str
    reason: str


class AgentOutcomeClassifier:
    """Label each agent record with an outcome; first match wins."""

    def classify(self, record: AgentRecord, now_ms: int) -> AgentOutcome:
        if self._is_dropped(record, now_ms):
            return AgentOutcome(
                DROPPED,
                f"registered but no tool calls within {_DROP_MINUTES} minutes of start")
        if self._is_stalled(record, now_ms):
            return AgentOutcome(
                STALLED, f"running with no update for {_STALL_MINUTES} minutes")
        if self._is_abandoned(record, now_ms):
            return AgentOutcome(
                ABANDONED,
                f"no update for {_ABANDON_MINUTES} minutes after earlier tool calls")
        if self._is_empty(record):
            return AgentOutcome(EMPTY, "finished without touching a file")
        return AgentOutcome(OK, "")

    def _is_dropped(self, record: AgentRecord, now_ms: int) -> bool:
        return (record.registered
                and record.tool_calls == 0
                and record.state != STATE_FINISHED
                and now_ms - record.started_ms > DROP_LIMIT_MS)

    def _is_stalled(self, record: AgentRecord, now_ms: int) -> bool:
        # OpenCode's raw "busy" status is translated to running, so running is
        # the only record state that means an agent is still working.
        return (record.state == STATE_RUNNING
                and now_ms - record.updated_ms >= STALL_LIMIT_MS)

    def _is_abandoned(self, record: AgentRecord, now_ms: int) -> bool:
        # A record stores only the current state, so "never reported finished"
        # is the same check as not finished right now.
        return (record.state not in (STATE_FINISHED, STATE_RUNNING)
                and record.tool_calls > 0
                and now_ms - record.updated_ms >= ABANDON_LIMIT_MS)

    def _is_empty(self, record: AgentRecord) -> bool:
        return (record.state == STATE_FINISHED
                and (record.tool_calls == 0 or record.last_file == ""))
