"""HTTP routes to list, add and remove the chat threads of an orchestrator."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from workbench.chat_backend_resolver import ChatBackendResolver
from workbench.orchestrator_directory import OrchestratorDirectory
from workbench.thread_registry import THREAD_SEPARATOR, ChatThread, ThreadRegistry


class ThreadRoutes:
    """GET, POST and DELETE the chat threads registered for one orchestrator."""

    def __init__(self, directory: OrchestratorDirectory, threads: ThreadRegistry,
                 resolver: ChatBackendResolver) -> None:
        self._directory = directory
        self._threads = threads
        self._resolver = resolver
        self.routes = APIRouter()
        self.routes.add_api_route(
            "/api/chat/{name}/threads", self.list_threads, methods=["GET"])
        self.routes.add_api_route(
            "/api/chat/{name}/threads", self.add_thread, methods=["POST"])
        self.routes.add_api_route(
            "/api/chat/{name}/threads/{thread_id}", self.remove_thread,
            methods=["DELETE"])

    async def list_threads(self, name: str) -> dict[str, list[dict[str, str]]]:
        self._require_orchestrator(name)
        return {"threads": [self._view(thread)
                            for thread in self._threads.list_threads(name)]}

    async def add_thread(self, name: str) -> dict[str, str]:
        self._require_orchestrator(name)
        return self._view(self._threads.add(name))

    async def remove_thread(self, name: str, thread_id: str) -> dict[str, bool]:
        thread = self._thread_of(name, thread_id)
        self._threads.remove(thread.name)
        await self._resolver.forget(thread.name)
        return {"ok": True}

    def _require_orchestrator(self, name: str) -> None:
        """404 unless name is a plain orchestrator; main~t1 is a thread."""
        if THREAD_SEPARATOR in name or self._directory.folder_of(name) == "":
            raise HTTPException(status_code=404)

    def _thread_of(self, orchestrator: str, thread_id: str) -> ChatThread:
        """404 unless the orchestrator owns a thread with this id."""
        for thread in self._threads.list_threads(orchestrator):
            if thread.thread_id == thread_id:
                return thread
        raise HTTPException(status_code=404)

    def _view(self, thread: ChatThread) -> dict[str, str]:
        mark = self._resolver.backend_of(thread.name).traits.tab_mark
        return {"name": thread.name, "thread_id": thread.thread_id,
                "label": thread.label, "mark": mark}
