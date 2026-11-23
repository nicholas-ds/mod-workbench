"""HTTP routes that show the research handoff report and nudge a chat."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from workbench.handoff.handoff_nudger import HandoffNudger, HandoffScanSource


class NudgePost(BaseModel):
    """Body of one handoff nudge post."""

    model_config = ConfigDict(frozen=True)

    kind: str
    target: str


class HandoffRoutes:
    """GET /api/handoff shows the report; POST /api/handoff/nudge nudges a chat."""

    def __init__(self, scanner: HandoffScanSource, nudger: HandoffNudger) -> None:
        self._scanner = scanner
        self._nudger = nudger
        self.routes = APIRouter()
        self.routes.add_api_route("/api/handoff", self.report, methods=["GET"])
        self.routes.add_api_route("/api/handoff/nudge", self.nudge, methods=["POST"])

    def report(self) -> dict[str, object]:
        return asdict(self._scanner.scan())

    async def nudge(self, body: NudgePost) -> dict[str, bool]:
        if not await self._nudger.nudge(body.kind, body.target):
            raise HTTPException(status_code=404)
        return {"nudged": True}
