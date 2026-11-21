"""In-memory agent records built from agent events (Task T1b).

The registry applies `AgentEvent`s to frozen `AgentRecord`s, persists them
through the `AgentStore`, and answers with a sorted `AgentView` snapshot.
"""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, replace
from typing import TYPE_CHECKING, Callable

from workbench.agent_event import (
    OPENCODE_SOURCE,
    STATE_FINISHED,
    STATE_RUNNING,
    AgentEvent,
)
from workbench.agent_outcome import AgentOutcomeClassifier

if TYPE_CHECKING:
    from workbench.agent_store import AgentStore

STALLED_STATE = "stalled"
UNREGISTERED_STATE = "unregistered"

_STALLED_SECONDS = 180.0
_FINISHED_KEEP_SECONDS = 600.0
_ABANDONED_SECONDS = 1800.0


@dataclass(frozen=True)
class AgentRecord:
    agent_id: str
    source: str
    parent_id: str
    cwd: str
    state: str
    title: str
    last_tool: str
    last_file: str
    progress: str
    tool_calls: int
    started_ms: int
    updated_ms: int
    registered: bool
    orchestrator: str


@dataclass(frozen=True)
class AgentView(AgentRecord):
    shown_state: str = ""
    age_seconds: int = 0
    outcome: str = ""
    outcome_reason: str = ""


class AgentRegistry:
    """Apply agent events and answer with a sorted view snapshot."""

    def __init__(self, store: AgentStore,
                 clock_ms: Callable[[], int] = lambda: int(time.time() * 1000),
                 stalled_seconds: float = _STALLED_SECONDS,
                 finished_keep_seconds: float = _FINISHED_KEEP_SECONDS,
                 outcome_classifier: AgentOutcomeClassifier | None = None) -> None:
        self._store = store
        self._clock_ms = clock_ms
        self._stalled_seconds = stalled_seconds
        self._finished_keep_seconds = finished_keep_seconds
        self._outcome_classifier = (outcome_classifier
                                    if outcome_classifier is not None
                                    else AgentOutcomeClassifier())
        self._records: dict[str, AgentRecord] = {
            record.agent_id: record for record in store.load()}

    def apply(self, event: AgentEvent) -> None:
        merged = self._merged(self._records.get(event.agent_id), event)
        self._records[event.agent_id] = merged
        self._store.save(list(self._records.values()))

    def register(self, agent_id: str, title: str, cwd: str, orchestrator: str) -> None:
        registered = self._registered(self._records.get(agent_id), agent_id,
                                      title, cwd, orchestrator)
        self._records[agent_id] = registered
        self._store.save(list(self._records.values()))

    def snapshot(self) -> list[AgentView]:
        now_ms = self._clock_ms()
        kept = [record for record in self._records.values()
                if self._keep(record, now_ms)]
        views = [self._view(record, now_ms) for record in kept]
        views.sort(key=lambda view: view.updated_ms, reverse=True)
        return views

    def _merged(self, old: AgentRecord | None, event: AgentEvent) -> AgentRecord:
        if old is None:
            return AgentRecord(
                agent_id=event.agent_id, source=event.source,
                parent_id=event.parent_id, cwd=event.cwd, state=event.state,
                title=event.title, last_tool=event.last_tool,
                last_file=event.last_file, progress=event.progress,
                tool_calls=1 if event.counts_tool else 0,
                started_ms=event.at_ms, updated_ms=event.at_ms,
                registered=False, orchestrator="")
        return replace(
            old,
            parent_id=event.parent_id or old.parent_id,
            cwd=event.cwd or old.cwd,
            state=event.state,
            title=event.title or old.title,
            last_tool=event.last_tool or old.last_tool,
            last_file=event.last_file or old.last_file,
            progress=event.progress or old.progress,
            tool_calls=old.tool_calls + (1 if event.counts_tool else 0),
            updated_ms=event.at_ms,
        )

    def _registered(self, old: AgentRecord | None, agent_id: str, title: str,
                    cwd: str, orchestrator: str) -> AgentRecord:
        if old is not None:
            return replace(old, title=title or old.title, cwd=cwd or old.cwd,
                           registered=True,
                           orchestrator=orchestrator or old.orchestrator)
        now_ms = self._clock_ms()
        return AgentRecord(
            agent_id=agent_id, source=OPENCODE_SOURCE, parent_id="", cwd=cwd,
            state=STATE_RUNNING, title=title, last_tool="", last_file="",
            progress="", tool_calls=0, started_ms=now_ms, updated_ms=now_ms,
            registered=True, orchestrator=orchestrator)

    def _keep(self, record: AgentRecord, now_ms: int) -> bool:
        age = self._age(record, now_ms)
        if age >= _ABANDONED_SECONDS + self._finished_keep_seconds:
            return False
        if record.state != STATE_FINISHED:
            return True
        return age < self._finished_keep_seconds

    def _age(self, record: AgentRecord, now_ms: int) -> float:
        return (now_ms - record.updated_ms) / 1000.0

    def _view(self, record: AgentRecord, now_ms: int) -> AgentView:
        age_seconds = max(0, int(self._age(record, now_ms)))
        outcome = self._outcome_classifier.classify(record, now_ms)
        return AgentView(**asdict(record),
                         shown_state=self._shown_state(record, age_seconds),
                         age_seconds=age_seconds,
                         outcome=outcome.label, outcome_reason=outcome.reason)

    def _shown_state(self, record: AgentRecord, age_seconds: int) -> str:
        if age_seconds >= _ABANDONED_SECONDS:
            return STATE_FINISHED
        if record.state != STATE_RUNNING:
            return record.state
        if age_seconds >= self._stalled_seconds:
            return STALLED_STATE
        if record.source == OPENCODE_SOURCE and not record.registered:
            return UNREGISTERED_STATE
        return record.state
