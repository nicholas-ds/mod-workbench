"""Route tests for AgentRoutes: events, workers, agents with TestClient."""

from typing import Callable

from fastapi import FastAPI
from fastapi.testclient import TestClient

from test_agent_registry import FakeClock
from workbench.agent_registry import AgentRegistry
from workbench.agent_store import AgentStore
from workbench.claude_translator import ClaudeEventTranslator
from workbench.opencode_translator import OpencodeEventTranslator
from workbench.routes_agents import AgentRoutes


def make_client(
    chat_session_ids: Callable[[], frozenset[str]] = frozenset,
) -> tuple[TestClient, FakeClock]:
    clock = FakeClock()
    registry = AgentRegistry(AgentStore(None), clock_ms=clock)
    routes = AgentRoutes(registry, ClaudeEventTranslator(),
                         OpencodeEventTranslator(), clock_ms=clock,
                         chat_session_ids=chat_session_ids)
    app = FastAPI()
    app.include_router(routes.routes)
    return TestClient(app), clock


def test_claude_event_creates_agent() -> None:
    client, _ = make_client()
    response = client.post("/api/events/claude", json={
        "session_id": "s1", "hook_event_name": "UserPromptSubmit", "cwd": "E:/repo"})
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    agent = client.get("/api/agents").json()["agents"][0]
    assert agent["agent_id"] == "s1"
    assert agent["source"] == "claude"
    assert agent["shown_state"] == "running"


def test_opencode_event_creates_agent() -> None:
    client, _ = make_client()
    response = client.post("/api/events/opencode", json={
        "session_id": "s2", "type": "session.status", "status": "busy"})
    assert response.status_code == 200
    agent = client.get("/api/agents").json()["agents"][0]
    assert agent["agent_id"] == "s2"
    assert agent["source"] == "opencode"


def test_malformed_and_ignored_bodies_answer_ok() -> None:
    client, _ = make_client()
    raw = client.post("/api/events/claude", content=b"{not json",
                      headers={"content-type": "application/json"})
    assert raw.status_code == 200
    assert raw.json() == {"ok": True}
    ignored = client.post("/api/events/claude", json={"hook_event_name": "Stop"})
    assert ignored.status_code == 200
    assert client.get("/api/agents").json()["agents"] == []


def test_workers_route_registers_agent() -> None:
    client, _ = make_client()
    response = client.post("/api/workers", json={
        "session_id": "w1", "title": "Board worker",
        "directory": "E:/repos/mods", "orchestrator": "glm"})
    assert response.status_code == 200
    agent = client.get("/api/agents").json()["agents"][0]
    assert agent["agent_id"] == "w1"
    assert agent["title"] == "Board worker"
    assert agent["orchestrator"] == "glm"
    assert agent["registered"] is True


def test_agents_route_returns_view_fields() -> None:
    client, clock = make_client()
    client.post("/api/events/opencode", json={
        "session_id": "s1", "type": "session.status", "status": "busy"})
    clock.advance(60)
    agents = client.get("/api/agents").json()["agents"]
    assert len(agents) == 1
    assert agents[0]["age_seconds"] == 60
    assert agents[0]["shown_state"] == "unregistered"


def test_app_chat_claude_event_is_skipped() -> None:
    client, _ = make_client(chat_session_ids=lambda: frozenset({"chat-session-1"}))
    response = client.post("/api/events/claude", json={
        "session_id": "chat-session-1", "hook_event_name": "UserPromptSubmit",
        "cwd": "E:/repo"})
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert client.get("/api/agents").json()["agents"] == []


def test_claude_event_from_other_session_creates_agent() -> None:
    client, _ = make_client(chat_session_ids=lambda: frozenset({"chat-session-1"}))
    response = client.post("/api/events/claude", json={
        "session_id": "s1", "hook_event_name": "UserPromptSubmit", "cwd": "E:/repo"})
    assert response.status_code == 200
    agent = client.get("/api/agents").json()["agents"][0]
    assert agent["agent_id"] == "s1"
    assert agent["source"] == "claude"
