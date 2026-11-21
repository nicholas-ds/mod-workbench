"""HTTP routes for agent events, worker registration and the agent list (Task T1b).

Event routes answer 200 with `{"ok": true}` always: an ignored or malformed
body is not a server error.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Callable, Union

from fastapi import APIRouter, Request

from workbench.agent_registry import AgentRegistry, AgentView
from workbench.claude_translator import ClaudeEventTranslator
from workbench.opencode_translator import OpencodeEventTranslator

Translator = Union[ClaudeEventTranslator, OpencodeEventTranslator]


class AgentRoutes:
    """POST agent events and worker registrations, GET the agent snapshot."""

    def __init__(self, registry: AgentRegistry, claude_translator: ClaudeEventTranslator,
                 opencode_translator: OpencodeEventTranslator,
                 clock_ms: Callable[[], int],
                 chat_session_ids: Callable[[], frozenset[str]] = frozenset) -> None:
        self._registry = registry
        self._claude, self._opencode = claude_translator, opencode_translator
        self._clock_ms = clock_ms
        self._chat_session_ids = chat_session_ids
        self.routes = APIRouter()
        self.routes.add_api_route("/api/events/claude", self.claude_events, methods=["POST"])
        self.routes.add_api_route("/api/events/opencode", self.opencode_events, methods=["POST"])
        self.routes.add_api_route("/api/workers", self.workers, methods=["POST"])
        self.routes.add_api_route("/api/agents", self.agents, methods=["GET"])

    async def claude_events(self, request: Request) -> dict[str, bool]:
        await self._apply_payload(request, self._claude, skip_ids=self._chat_session_ids())
        return {"ok": True}

    async def opencode_events(self, request: Request) -> dict[str, bool]:
        await self._apply_payload(request, self._opencode)
        return {"ok": True}

    async def workers(self, request: Request) -> dict[str, bool]:
        payload = await self._json_object(request)
        if payload is not None:
            self._register_worker(payload)
        return {"ok": True}

    def agents(self) -> dict[str, list[dict[str, object]]]:
        views: list[AgentView] = self._registry.snapshot()
        return {"agents": [asdict(view) for view in views]}

    async def _apply_payload(self, request: Request, translator: Translator,
                             skip_ids: frozenset[str] = frozenset()) -> None:
        payload = await self._json_object(request)
        if payload is None:
            return
        if str(payload.get("session_id", "")) in skip_ids:
            return
        event = translator.translate(payload, self._clock_ms())
        if event is not None:
            self._registry.apply(event)

    def _register_worker(self, payload: dict[str, object]) -> None:
        agent_id = str(payload.get("session_id", ""))
        if not agent_id:
            return
        self._registry.register(
            agent_id,
            str(payload.get("title", "")),
            str(payload.get("directory", "")),
            str(payload.get("orchestrator", "")),
        )

    async def _json_object(self, request: Request) -> dict[str, object] | None:
        try:
            payload: object = await request.json()
        except ValueError:
            return None
        return payload if isinstance(payload, dict) else None
