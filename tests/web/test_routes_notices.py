from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from workbench.core.config import ModConfig
from workbench.notices.delivery_view import DeliveryViewBuilder
from workbench.notices.notice_types import DeliveryRecord, DeliveryState, Notice
from workbench.notices.owner_id import OwnerId, OwnerKind
from workbench.notices.owner_inbox import OwnerInbox
from workbench.web.routes_notices import NoticesRoutes


class FakeRegistry:
    """Serve one fixed ModConfig, 404 for any other name."""

    def __init__(self, cfg: ModConfig) -> None:
        self._cfg = cfg

    def require(self, name: str) -> ModConfig:
        if name == self._cfg.name:
            return self._cfg
        raise HTTPException(status_code=404, detail=f"unknown mod: {name}")


class FakeDispatcher:
    """Mark the record delivered and store the update, like the real pipeline."""

    def __init__(self, inbox: OwnerInbox) -> None:
        self._inbox = inbox

    def redeliver(self, record: DeliveryRecord) -> DeliveryRecord:
        updated = DeliveryRecord(notice_id=record.notice_id, owner=record.owner,
                                 state=DeliveryState.DELIVERED,
                                 attempts=record.attempts + 1,
                                 last_try="2026-11-23T11:00:00", error="")
        self._inbox.update(updated)
        return updated


def make_client(tmp_path: Path) -> tuple[TestClient, OwnerInbox]:
    inbox = OwnerInbox(tmp_path / "notices")
    cfg = ModConfig(name="demo", repo=tmp_path, platform=tmp_path, screens=(),
                    boards=tmp_path, status=tmp_path, tracking=tmp_path, log=tmp_path,
                    briefs=tmp_path, exports=tmp_path)

    def inbox_of(_cfg: ModConfig) -> OwnerInbox:
        return inbox

    def dispatcher_of(_cfg: ModConfig) -> FakeDispatcher:
        return FakeDispatcher(inbox)

    app = FastAPI()
    app.include_router(NoticesRoutes(FakeRegistry(cfg), inbox_of, dispatcher_of,
                                     DeliveryViewBuilder()).routes)
    return TestClient(app), inbox


def _write(inbox: OwnerInbox, notice_id: str, created: str, owner: OwnerId) -> None:
    notice = Notice(id=notice_id, owner=owner, board="b1", event="answer",
                    file_path="boards/open/b1/board.md", line="hello", created=created)
    inbox.write(notice, resolution_known=True)


def test_get_lists_records_of_all_owners_newest_first(tmp_path: Path) -> None:
    client, inbox = make_client(tmp_path)
    _write(inbox, "n1", "2026-11-23T09:00:00", OwnerId(OwnerKind.PANE, "boards-1"))
    _write(inbox, "n2", "2026-11-23T10:00:00", OwnerId(OwnerKind.CHAT, "review"))

    notices = client.get("/api/mods/demo/notices").json()["notices"]

    assert [notice["notice_id"] for notice in notices] == ["n2", "n1"]
    assert [notice["label"] for notice in notices] == ["Waiting to deliver"] * 2


def test_get_is_empty_when_nothing_was_delivered(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)

    assert client.get("/api/mods/demo/notices").json() == {"notices": []}


def test_post_retry_redelivers_and_returns_the_new_view(tmp_path: Path) -> None:
    client, inbox = make_client(tmp_path)
    _write(inbox, "n1", "2026-11-23T09:00:00", OwnerId(OwnerKind.PANE, "boards-1"))

    response = client.post("/api/mods/demo/notices/n1/retry")
    notice = response.json()["notice"]

    assert (response.status_code, notice["state"]) == (200, "delivered")
    assert notice["label"] == "Delivered"
    assert inbox.all_records()[0].state is DeliveryState.DELIVERED


def test_unknown_notice_and_unknown_mod_are_404(tmp_path: Path) -> None:
    client, _ = make_client(tmp_path)

    assert client.post("/api/mods/demo/notices/ghost/retry").status_code == 404
    assert client.get("/api/mods/other/notices").status_code == 404
