"""Tests for AgentOutcomeClassifier: one test per outcome, one per limit."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from test_agent_registry import FakeClock
from workbench.agent_event import STATE_FINISHED, STATE_IDLE
from workbench.agent_outcome import (
    ABANDON_LIMIT_MS,
    DROP_LIMIT_MS,
    STALL_LIMIT_MS,
    AgentOutcomeClassifier,
)
from workbench.agent_registry import AgentRecord, AgentRegistry
from workbench.agent_store import AgentStore
from workbench.claude_translator import ClaudeEventTranslator
from workbench.opencode_translator import OpencodeEventTranslator
from workbench.routes_agents import AgentRoutes

NOW_MS = 10_000_000


def make_record(**fields: object) -> AgentRecord:
    values: dict[str, object] = dict(
        agent_id="s1", source="opencode", parent_id="", cwd="E:/repo",
        state="running", title="", last_tool="", last_file="", progress="",
        tool_calls=0, started_ms=NOW_MS, updated_ms=NOW_MS,
        registered=False, orchestrator="")
    values.update(fields)
    return AgentRecord(**values)


def label_of(record: AgentRecord, now_ms: int = NOW_MS) -> str:
    return AgentOutcomeClassifier().classify(record, now_ms).label


def test_dropped_registered_without_tool_calls() -> None:
    record = make_record(registered=True, tool_calls=0,
                         started_ms=NOW_MS - DROP_LIMIT_MS - 1,
                         updated_ms=NOW_MS - 1000)
    assert label_of(record) == "dropped"


def test_stalled_running_without_update() -> None:
    record = make_record(tool_calls=3, updated_ms=NOW_MS - STALL_LIMIT_MS)
    assert label_of(record) == "stalled"


def test_abandoned_idle_after_tool_calls() -> None:
    record = make_record(state=STATE_IDLE, registered=True, tool_calls=2,
                         started_ms=NOW_MS - ABANDON_LIMIT_MS - 5000,
                         updated_ms=NOW_MS - ABANDON_LIMIT_MS)
    assert label_of(record) == "abandoned"


def test_empty_finished_without_file_or_tools() -> None:
    no_file = make_record(state=STATE_FINISHED, tool_calls=4, last_file="")
    no_tools = make_record(state=STATE_FINISHED, tool_calls=0,
                           last_file="main.py")
    assert label_of(no_file) == "empty"
    assert label_of(no_tools) == "empty"


def test_ok_running_agent_with_recent_activity() -> None:
    record = make_record(registered=True, tool_calls=5, last_file="main.py",
                         updated_ms=NOW_MS - 1000)
    outcome = AgentOutcomeClassifier().classify(record, NOW_MS)
    assert outcome.label == "ok"
    assert outcome.reason == ""


def test_running_outranks_abandoned_when_silent_beyond_limit() -> None:
    record = make_record(tool_calls=6,
                         started_ms=NOW_MS - ABANDON_LIMIT_MS - 5000,
                         updated_ms=NOW_MS - ABANDON_LIMIT_MS - 1000)
    assert label_of(record) == "stalled"


def test_drop_limit_boundary() -> None:
    at_limit = make_record(registered=True, started_ms=NOW_MS - DROP_LIMIT_MS)
    past_limit = make_record(registered=True,
                             started_ms=NOW_MS - DROP_LIMIT_MS - 1)
    assert label_of(at_limit) == "ok"
    assert label_of(past_limit) == "dropped"


def test_stall_limit_boundary() -> None:
    just_before = make_record(tool_calls=1,
                              updated_ms=NOW_MS - STALL_LIMIT_MS + 1)
    at_limit = make_record(tool_calls=1, updated_ms=NOW_MS - STALL_LIMIT_MS)
    assert label_of(just_before) == "ok"
    assert label_of(at_limit) == "stalled"


def test_abandon_limit_boundary() -> None:
    just_before = make_record(state=STATE_IDLE, tool_calls=1,
                              updated_ms=NOW_MS - ABANDON_LIMIT_MS + 1)
    at_limit = make_record(state=STATE_IDLE, tool_calls=1,
                           updated_ms=NOW_MS - ABANDON_LIMIT_MS)
    assert label_of(just_before) == "ok"
    assert label_of(at_limit) == "abandoned"


def test_registry_view_carries_outcome() -> None:
    clock = FakeClock()
    registry = AgentRegistry(AgentStore(None), clock_ms=clock)
    registry.register("w1", "Worker", "E:/repo", "glm")
    view = registry.snapshot()[0]
    assert view.outcome == "ok"
    assert view.outcome_reason == ""
    clock.advance(DROP_LIMIT_MS // 1000 + 1)
    assert registry.snapshot()[0].outcome == "dropped"


def test_agents_route_serializes_outcome_fields() -> None:
    clock = FakeClock()
    registry = AgentRegistry(AgentStore(None), clock_ms=clock)
    registry.register("w1", "Worker", "E:/repo", "glm")
    routes = AgentRoutes(registry, ClaudeEventTranslator(),
                         OpencodeEventTranslator(), clock_ms=clock)
    app = FastAPI()
    app.include_router(routes.routes)
    agents = TestClient(app).get("/api/agents").json()["agents"]
    assert agents[0]["outcome"] == "ok"
    assert agents[0]["outcome_reason"] == ""
