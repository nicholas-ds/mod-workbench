"""Tests for AgentRegistry: merge rules, shown states, and AgentStore persistence."""

from dataclasses import asdict
from pathlib import Path

from fake_clock import FakeClock
from workbench.agents.agent_event import AgentEvent
from workbench.agents.agent_registry import AgentRecord, AgentRegistry
from workbench.agents.agent_store import AgentStore


def make_registry(clock: FakeClock, path: Path | None = None) -> AgentRegistry:
    return AgentRegistry(AgentStore(path), clock_ms=clock)


def running_event(agent_id: str, at_ms: int, **fields: object) -> AgentEvent:
    return AgentEvent(source="opencode", agent_id=agent_id, at_ms=at_ms,
                      state="running", **fields)


def test_apply_creates_record() -> None:
    clock = FakeClock()
    registry = make_registry(clock)
    registry.apply(running_event("s1", 1_000_000, cwd="E:/repo", counts_tool=True))
    registry.apply(running_event("s1", 1_000_000, counts_tool=True))
    view = registry.snapshot()[0]
    assert view.agent_id == "s1"
    assert view.source == "opencode"
    assert view.state == "running"
    assert view.started_ms == 1_000_000
    assert view.tool_calls == 2
    assert view.registered is False


def test_apply_empty_strings_keep_old_values() -> None:
    clock = FakeClock()
    registry = make_registry(clock)
    registry.apply(running_event("s1", 1000, cwd="E:/repo", title="Worker",
                                 last_tool="Edit main.py", progress="step 1"))
    registry.apply(AgentEvent(source="opencode", agent_id="s1", at_ms=2000,
                              state="idle"))
    view = registry.snapshot()[0]
    assert view.cwd == "E:/repo"
    assert view.title == "Worker"
    assert view.last_tool == "Edit main.py"
    assert view.progress == "step 1"
    assert view.state == "idle"
    assert view.updated_ms == 2000


def test_stalled_after_stalled_seconds() -> None:
    clock = FakeClock()
    registry = make_registry(clock)
    registry.apply(AgentEvent(source="claude", agent_id="s1",
                              at_ms=clock.now_ms, state="running"))
    clock.advance(179)
    assert registry.snapshot()[0].shown_state == "running"
    clock.advance(1)
    view = registry.snapshot()[0]
    assert view.shown_state == "stalled"
    assert view.age_seconds == 180


def test_unregistered_then_registered() -> None:
    clock = FakeClock()
    registry = make_registry(clock)
    registry.apply(running_event("s1", clock.now_ms))
    assert registry.snapshot()[0].shown_state == "unregistered"
    registry.register("s1", "T1 worker", "E:/repos/mods", "glm")
    view = registry.snapshot()[0]
    assert view.registered is True
    assert view.title == "T1 worker"
    assert view.cwd == "E:/repos/mods"
    assert view.orchestrator == "glm"
    assert view.shown_state == "running"


def test_register_creates_missing_record() -> None:
    clock = FakeClock()
    registry = make_registry(clock)
    registry.register("w1", "Board worker", "E:/repo", "glm")
    view = registry.snapshot()[0]
    assert view.source == "opencode"
    assert view.state == "running"
    assert view.registered is True
    assert view.started_ms == clock.now_ms
    assert view.updated_ms == clock.now_ms


def test_finished_record_dropped_after_keep_seconds() -> None:
    clock = FakeClock()
    registry = make_registry(clock)
    registry.apply(AgentEvent(source="opencode", agent_id="s1",
                              at_ms=clock.now_ms, state="finished"))
    clock.advance(599)
    assert len(registry.snapshot()) == 1
    clock.advance(2)
    assert registry.snapshot() == []


def test_claude_record_silent_30_minutes_shows_finished() -> None:
    clock = FakeClock()
    registry = make_registry(clock)
    registry.apply(AgentEvent(source="claude", agent_id="s1",
                              at_ms=clock.now_ms, state="running"))
    clock.advance(1900)
    assert registry.snapshot()[0].shown_state == "finished"


def test_snapshot_sorted_by_updated_desc() -> None:
    clock = FakeClock()
    registry = make_registry(clock)
    registry.apply(running_event("old", 1000))
    registry.apply(running_event("new", 5000))
    assert [view.agent_id for view in registry.snapshot()] == ["new", "old"]


def test_store_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "status" / "agents.json"
    registry = make_registry(FakeClock(), path)
    registry.apply(running_event("s1", 1000, title="Worker", counts_tool=True))
    registry.register("s1", "Worker", "E:/repo", "glm")
    saved = AgentStore(path).load()
    assert saved == [AgentRecord(agent_id="s1", source="opencode", parent_id="",
                                 cwd="E:/repo", state="running", title="Worker",
                                 last_tool="", last_file="", progress="",
                                 tool_calls=1, started_ms=1000, updated_ms=1000,
                                 registered=True, orchestrator="glm")]
    loaded = make_registry(FakeClock(1000), path).snapshot()
    assert [view.agent_id for view in loaded] == ["s1"]
    assert loaded[0].registered is True


def test_store_load_without_path_or_file(tmp_path: Path) -> None:
    assert AgentStore(None).load() == []
    assert AgentStore(tmp_path / "missing.json").load() == []


def test_store_load_corrupt_file(tmp_path: Path) -> None:
    path = tmp_path / "agents.json"
    path.write_text("{not json", encoding="utf-8")
    assert AgentStore(path).load() == []
    path.write_text('{"no_agents": 1}', encoding="utf-8")
    assert AgentStore(path).load() == []


def test_abandoned_worker_shows_finished_then_disappears() -> None:
    clock = FakeClock()
    registry = make_registry(clock)
    registry.apply(running_event("s1", clock.now_ms))
    clock.advance(1800)
    assert registry.snapshot()[0].shown_state == "finished"
    clock.advance(600)
    assert registry.snapshot() == []
