"""HTTP route that wakes every orchestrator chat."""

from __future__ import annotations

from fastapi import APIRouter

from workbench.wake_broadcaster import WakeBroadcaster


class WakeRoutes:
    """POST /api/wake sends the wake turn to every chat."""

    def __init__(self, broadcaster: WakeBroadcaster) -> None:
        self._broadcaster = broadcaster
        self.routes = APIRouter()
        self.routes.add_api_route("/api/wake", self.wake, methods=["POST"])

    async def wake(self) -> dict[str, list[str]]:
        return {"woken": list(await self._broadcaster.wake_all())}
