"""Notice routes of one mod: list delivery records and retry one."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, HTTPException

from workbench.core.config import ModConfig
from workbench.mods.mod_registry import ModRegistry
from workbench.notices.delivery_view import DeliveryViewBuilder
from workbench.notices.notice_dispatcher import NoticeDispatcher
from workbench.notices.notice_types import DeliveryRecord
from workbench.notices.owner_inbox import OwnerInbox


class NoticesRoutes:
    """Notice routes of one mod: list delivery records and retry one."""

    def __init__(self, registry: ModRegistry,
                 inbox_of: Callable[[ModConfig], OwnerInbox],
                 dispatcher_of: Callable[[ModConfig], NoticeDispatcher],
                 view_builder: DeliveryViewBuilder) -> None:
        self._registry, self._inbox_of = registry, inbox_of
        self._dispatcher_of, self._views = dispatcher_of, view_builder
        self.routes = APIRouter()
        self.routes.add_api_route("/api/mods/{name}/notices", self.notices, methods=["GET"])
        self.routes.add_api_route("/api/mods/{name}/notices/{notice_id}/retry", self.retry,
                                  methods=["POST"])

    def notices(self, name: str) -> dict[str, object]:
        """List every delivery record of the mod, newest first."""
        cfg = self._registry.require(name)
        inbox = self._inbox_of(cfg)
        views = [self._views.build(record, self._board_of(inbox, record))
                 for record in inbox.all_records()]
        return {"notices": [view.as_json() for view in views]}

    def retry(self, name: str, notice_id: str) -> dict[str, object]:
        """Redeliver one record and return its new view; 404 when unknown."""
        cfg = self._registry.require(name)
        record = self._record(cfg, notice_id)
        delivered = self._dispatcher_of(cfg).redeliver(record)
        board = self._board_of(self._inbox_of(cfg), delivered)
        return {"notice": self._views.build(delivered, board).as_json()}

    @staticmethod
    def _board_of(inbox: OwnerInbox, record: DeliveryRecord) -> str:
        notice = inbox.notice_of(record)
        return notice.board if notice else ""

    def _record(self, cfg: ModConfig, notice_id: str) -> DeliveryRecord:
        for record in self._inbox_of(cfg).all_records():
            if record.notice_id == notice_id:
                return record
        raise HTTPException(status_code=404, detail=f"unknown notice: {notice_id}")
