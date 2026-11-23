"""`GET /api/events`: server-sent events for file changes."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from workbench.mods.mod_registry import ModRegistry
from workbench.core.watch import FileChangeWatcher


class EventsRoutes:
    """`GET /api/events`: server-sent events for file changes."""

    def __init__(self, watcher: FileChangeWatcher, registry: ModRegistry) -> None:
        self._watcher, self._registry = watcher, registry
        self.routes = APIRouter()
        self.routes.add_api_route("/api/events", self.stream, methods=["GET"])

    def stream(self) -> StreamingResponse:
        return StreamingResponse(self._events(), media_type="text/event-stream")

    async def _events(self) -> AsyncIterator[str]:
        paths = [result.repo for result in self._registry.all()]
        async for batch in self._watcher.changes(paths):
            yield f"data: {json.dumps({'changed': sorted(str(p) for p in batch)})}\n\n"
