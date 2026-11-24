from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from workbench.core.config import ModConfig
from workbench.notices.active_loop_filter import ActiveLoopFilter
from workbench.notices.loop_types import LoopSnapshot, LoopStage
from workbench.notices.notice_types import Notice
from workbench.notices.owner_id import OwnerId, OwnerKind
from workbench.notices.owner_inbox import OwnerInbox
from workbench.web.routes_loops import LoopRoutes

_NOW = datetime(2026, 11, 23, 12, 0, tzinfo=UTC)


class FakeRegistry:
    """Serve one fixed ModConfig, 404 for any other name."""

    def __init__(self, cfg: ModConfig) -> None:
        self._cfg = cfg

    def require(self, name: str) -> ModConfig:
        if name == self._cfg.name:
            return self._cfg
        raise HTTPException(status_code=404, detail=f"unknown mod: {name}")


class StubTracker:
    def __init__(self, snapshot: LoopSnapshot | None) -> None:
        self._snapshot = snapshot

    def track(self, _record: object) -> LoopSnapshot | None:
        return self._snapshot


def make_client(tmp_path: Path, stage: LoopStage | None = None,
                since: str = "2026-11-23T10:00:00") -> TestClient:
    snap = None if stage is None else LoopSnapshot(
        notice_id="n1", board="b1", owner="pane boards-1", stage=stage,
        reason="", since=since, last_action="", summary="", can_retry=False)
    inbox = OwnerInbox(tmp_path / "notices")
    notice = Notice(id="n1", owner=OwnerId(OwnerKind.PANE, "boards-1"), board="b1",
                    event="answer", file_path="boards/open/b1/board.md", line="hello",
                    created="2026-11-23T09:00:00")
    inbox.write(notice, resolution_known=True)
    cfg = ModConfig(name="demo", repo=tmp_path, platform=tmp_path, screens=(),
                    boards=tmp_path, status=tmp_path, tracking=tmp_path, log=tmp_path,
                    briefs=tmp_path, exports=tmp_path)
    app = FastAPI()
    app.include_router(LoopRoutes(FakeRegistry(cfg), lambda _cfg: StubTracker(snap),
                                  lambda _cfg: inbox, ActiveLoopFilter(),
                                  lambda: _NOW).routes)
    return TestClient(app)


def test_unknown_mod_is_404(tmp_path: Path) -> None:
    assert make_client(tmp_path).get("/api/mods/other/loops").status_code == 404


def test_working_loop_is_listed(tmp_path: Path) -> None:
    client = make_client(tmp_path, LoopStage.WORKING)
    loops = client.get("/api/mods/demo/loops").json()["loops"]
    assert loops[0]["stage"] == "working"


def test_untracked_record_gives_no_loops(tmp_path: Path) -> None:
    assert make_client(tmp_path).get("/api/mods/demo/loops").json() == {"loops": []}


def test_old_done_loop_is_filtered(tmp_path: Path) -> None:
    client = make_client(tmp_path, LoopStage.DONE,
                         since=(_NOW - timedelta(minutes=11)).isoformat())
    assert client.get("/api/mods/demo/loops").json() == {"loops": []}
