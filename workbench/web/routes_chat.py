"""HTTP routes for chat turns (SSE), stop, permission answers, resume, flip."""

from __future__ import annotations

import dataclasses
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from workbench.chat.chat_backend_resolver import ChatBackendResolver
from workbench.chat.chat_command import ChatCommand, SlashCommandParser
from workbench.chat.chat_event import ChatEvent
from workbench.chat.orchestrator_directory import OrchestratorDirectory
from workbench.chat.pending_permission_store import PendingPermissionStore
from workbench.chat.thread_registry import ChatThread, ThreadRegistry


DECISIONS = frozenset({"allow", "deny"})
UNKNOWN_BACKEND = "Unknown backend."


class ChatRoutes:
    """POST a chat turn as SSE events, GET the stream of the running turn,
    POST stop, POST a permission answer, GET the saved history, the listed
    sessions, the current session, the slash commands and the backend list,
    POST a resume and a backend flip.
    Every call resolves its backend through the ChatBackendResolver."""

    def __init__(self, resolver: ChatBackendResolver,
                 parser: SlashCommandParser,
                 directory: OrchestratorDirectory,
                 permissions: PendingPermissionStore,
                 threads: ThreadRegistry | None = None) -> None:
        self._resolver = resolver
        self._parser = parser
        self._directory = directory
        self._permissions = permissions
        self._threads = threads
        self.routes = APIRouter()
        self.routes.add_api_route("/api/chat", self.list_orchestrators, methods=["GET"])
        self.routes.add_api_route("/api/chat/backends", self.backends, methods=["GET"])
        self.routes.add_api_route("/api/chat/{name}", self.chat, methods=["POST"])
        self.routes.add_api_route(
            "/api/chat/{name}/stream", self.follow, methods=["GET"])
        self.routes.add_api_route(
            "/api/chat/{name}/history", self.load_history, methods=["GET"])
        self.routes.add_api_route(
            "/api/chat/{name}/session", self.session, methods=["GET"])
        self.routes.add_api_route(
            "/api/chat/{name}/sessions", self.sessions, methods=["GET"])
        self.routes.add_api_route(
            "/api/chat/{name}/resume", self.resume, methods=["POST"])
        self.routes.add_api_route(
            "/api/chat/{name}/commands", self.commands, methods=["GET"])
        self.routes.add_api_route("/api/chat/{name}/stop", self.stop, methods=["POST"])
        self.routes.add_api_route(
            "/api/chat/{name}/permission", self.permission, methods=["POST"])
        self.routes.add_api_route(
            "/api/chat/{name}/backend", self.set_backend, methods=["POST"])

    async def backends(self) -> dict[str, list[dict[str, object]]]:
        return {"backends": [traits.as_json()
                             for traits in self._resolver.all_traits()]}

    async def list_orchestrators(self) -> dict[str, list[dict[str, object]]]:
        entries: list[dict[str, object]] = [
            dataclasses.asdict(entry) for entry in self._directory.entries()]
        for entry in entries:
            name = str(entry["name"])
            entry["backend"] = self._resolver.backend_of(name).traits.key
        return {"orchestrators": entries}

    async def chat(self, name: str, request: Request) -> StreamingResponse:
        command = self._parse(name, await self._text(request))
        backend = self._resolver.backend_of(name)
        return StreamingResponse(
            self._sse(backend.run(name, command)), media_type="text/event-stream")

    async def follow(self, name: str) -> StreamingResponse:
        self._require_known(name)
        backend = self._resolver.backend_of(name)
        return StreamingResponse(
            self._sse(backend.follow(name)), media_type="text/event-stream")

    async def load_history(self, name: str) -> dict[str, list[dict[str, object]]]:
        self._require_known(name)
        events = await self._resolver.backend_of(name).history(name)
        return {"events": [
            dataclasses.asdict(event) for event in events]}

    async def session(self, name: str) -> dict[str, object]:
        self._require_known(name)
        backend = self._resolver.backend_of(name)
        view = await backend.session(name)
        return {
            "session_id": view.session_id,
            "folder": self._directory.folder_of(name),
            "running": backend.is_running(name),
            "context_percent": view.context_percent,
            "backend": backend.traits.key,
        }

    async def sessions(self, name: str) -> dict[str, list[dict[str, object]]]:
        self._require_known(name)
        backend = self._resolver.backend_of(name)
        rows = await backend.sessions(name, self._directory.folder_of(name))
        return {"sessions": [dataclasses.asdict(row) for row in rows]}

    async def resume(self, name: str, request: Request) -> dict[str, bool]:
        self._require_known(name)
        session_id = (await self._json_payload(request)).get("session_id")
        if not isinstance(session_id, str) or session_id == "":
            raise HTTPException(status_code=400)
        backend = self._resolver.backend_of(name)
        folder = self._directory.folder_of(name)
        ok = await backend.resume_session(name, folder, session_id)
        if not ok:
            raise HTTPException(status_code=409)
        return {"ok": True}

    async def commands(self, name: str) -> dict[str, list[dict[str, str]]]:
        self._require_known(name)
        rows = await self._resolver.backend_of(name).commands(name)
        return {"commands": [dataclasses.asdict(row) for row in rows]}

    async def stop(self, name: str) -> dict[str, bool]:
        self._require_known(name)
        await self._resolver.backend_of(name).stop(name)
        return {"ok": True}

    async def set_backend(self, name: str, request: Request) -> dict[str, object]:
        self._require_known(name)
        key = (await self._json_payload(request)).get("backend")
        if not isinstance(key, str):
            raise HTTPException(status_code=400)
        result = await self._resolver.flip(name, key)
        if not result.ok:
            if result.reason == UNKNOWN_BACKEND:
                raise HTTPException(status_code=400)
            raise HTTPException(status_code=409, detail=result.reason)
        return {"ok": True, "backend": key}

    async def permission(self, name: str, request: Request) -> dict[str, bool]:
        self._require_known(name)
        request_id, allowed = await self._permission_body(request)
        return {"ok": self._permissions.answer(request_id, allowed)}

    def _sse(self, events: AsyncIterator[ChatEvent]) -> AsyncIterator[str]:
        async def stream() -> AsyncIterator[str]:
            async for event in events:
                yield self._sse_line(event)
        return stream()

    def _sse_line(self, event: ChatEvent) -> str:
        return "data: " + json.dumps(dataclasses.asdict(event)) + "\n\n"

    async def _json_payload(self, request: Request) -> dict[str, object]:
        try:
            payload: object = await request.json()
        except ValueError:
            raise HTTPException(status_code=400) from None
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400)
        return payload

    async def _permission_body(self, request: Request) -> tuple[str, bool]:
        payload = await self._json_payload(request)
        request_id = payload.get("request_id")
        decision = payload.get("decision")
        if (not isinstance(request_id, str) or not isinstance(decision, str)
                or decision not in DECISIONS):
            raise HTTPException(status_code=400)
        return request_id, decision == "allow"

    async def _text(self, request: Request) -> str:
        payload = await self._json_payload(request)
        text = payload.get("text")
        if not isinstance(text, str):
            raise HTTPException(status_code=400)
        return text

    def _parse(self, name: str, text: str) -> ChatCommand:
        self._require_known(name)
        try:
            return self._parser.parse(text)
        except ValueError:
            raise HTTPException(status_code=400) from None

    def _require_known(self, name: str) -> None:
        if self._directory.folder_of(name) == "":
            raise HTTPException(status_code=404)
        if (self._threads is not None
                and ChatThread.split_name(name)[1] != ""
                and not self._threads.contains(name)):
            raise HTTPException(status_code=404)
