"""Tests: the messages API saves an author message file, or rejects the post."""

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from api_fixtures import make_client, make_mod_repo, make_other_repo
from workbench.boards.answer_store import AnswerStore
from workbench.boards.board_builder import BoardBuilder
from workbench.boards.board_repository import BoardRepository
from workbench.core.config import ModConfigLoader, ModDiscovery
from workbench.boards.front_matter import FrontMatterParser
from workbench.panes.message_writer import MessageWriter
from workbench.mods.mod_registry import ModRegistry
from workbench.mods.pane_directory import PaneDirectory
from workbench.panes.pane_registry import OrchestratorPane, PaneRegistry
from workbench.web.routes_messages import MessagesRoutes

MESSAGES_URL = "/api/mods/CityMod/messages"

PANE_FILE = Path("status") / "main-orchestrator.toml"


class FakePaneSender:
    """Record typed lines and report delivery."""

    def __init__(self) -> None:
        self.lines: list[str] = []

    def send(self, pane: OrchestratorPane, text: str) -> bool:
        self.lines.append(text)
        return True


def messages_client(root: Path, sender: FakePaneSender) -> TestClient:
    registry = ModRegistry(ModDiscovery(ModConfigLoader()), [root],
                           BoardRepository(FrontMatterParser(), BoardBuilder()),
                           AnswerStore())
    routes = MessagesRoutes(registry, MessageWriter(),
                            pane_registry=PaneRegistry(root / PANE_FILE),
                            pane_sender=sender)
    app = FastAPI()
    app.include_router(routes.routes)
    return TestClient(app)


def panes_client(root: Path, sender: FakePaneSender) -> TestClient:
    registry = ModRegistry(ModDiscovery(ModConfigLoader()), [root],
                           BoardRepository(FrontMatterParser(), BoardBuilder()),
                           AnswerStore())
    routes = MessagesRoutes(registry, MessageWriter(),
                            pane_registry=PaneRegistry(root / PANE_FILE),
                            pane_sender=sender,
                            workbench_root=root / "wb",
                            pane_directory=PaneDirectory(registry, root))
    app = FastAPI()
    app.include_router(routes.routes)
    return TestClient(app)



def test_post_message_creates_file(tmp_path: Path) -> None:
    repo = make_mod_repo(tmp_path)
    client = messages_client(tmp_path, FakePaneSender())
    response = client.post(MESSAGES_URL, json={
        "text": "Widen the panel",
        "context": {"view": "board", "board": "layout", "item": "shot.png",
                    "question": None}})
    assert response.status_code == 200
    assert response.json()["delivered"] is False
    message_id = response.json()["id"]
    text = (repo / "messages" / f"{message_id}.md").read_text(encoding="utf-8")
    assert "view: board\n" in text
    assert "board: layout\n" in text
    assert "item: shot.png\n" in text
    assert "question" not in text
    assert text.endswith("Widen the panel\n")


def test_post_message_delivers_line_to_orchestrator_pane(tmp_path: Path) -> None:
    repo = make_mod_repo(tmp_path)
    (tmp_path / "status").mkdir()
    (tmp_path / PANE_FILE).write_text('wmux_surface = "surf-1"\n', encoding="utf-8")
    sender = FakePaneSender()
    client = messages_client(tmp_path, sender)
    response = client.post(MESSAGES_URL, json={
        "text": "Widen the panel",
        "context": {"view": "board", "board": "layout"}})
    assert response.status_code == 200
    assert response.json()["delivered"] is True
    message_id = response.json()["id"]
    assert sender.lines[0].startswith(
        f"[workbench] mod=CityMod view=board board=layout id={message_id} | Widen the panel | ")
    assert f"messages{os.sep}replies{os.sep}{message_id}.md" in sender.lines[0]
    assert (repo / "messages").exists()


def test_unknown_mod_is_404(tmp_path: Path) -> None:
    make_mod_repo(tmp_path)
    client = make_client(tmp_path)
    response = client.post("/api/mods/NoMod/messages", json={
        "text": "hello", "context": {"view": "home"}})
    assert response.status_code == 404


def test_empty_text_is_400(tmp_path: Path) -> None:
    repo = make_mod_repo(tmp_path)
    client = make_client(tmp_path)
    response = client.post(MESSAGES_URL, json={
        "text": "   ", "context": {"view": "home"}})
    assert response.status_code == 400
    assert not (repo / "messages").exists()


def test_get_messages_returns_saved_message_newest_first(tmp_path: Path) -> None:
    repo = make_mod_repo(tmp_path)
    client = messages_client(tmp_path, FakePaneSender())
    client.post(MESSAGES_URL, json={
        "text": "Widen the panel", "context": {"view": "board", "board": "layout"}})
    response = client.get(MESSAGES_URL)
    assert response.status_code == 200
    messages = response.json()["messages"]
    assert len(messages) == 1
    message = messages[0]
    assert message["text"] == "Widen the panel"
    assert message["view"] == "board"
    assert message["board"] == "layout"
    assert message["reply"] is None
    assert message["done"] is False
    assert (repo / "messages" / f"{message['id']}.md").exists()


def test_real_app_wiring_serves_get_messages(tmp_path: Path) -> None:
    make_mod_repo(tmp_path)
    response = make_client(tmp_path).get(MESSAGES_URL)
    assert response.status_code == 200
    assert response.json() == {"messages": []}


def test_workbench_message_saves_in_workbench_folder_and_delivers(tmp_path: Path) -> None:
    make_mod_repo(tmp_path)
    (tmp_path / PANE_FILE).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / PANE_FILE).write_text('wmux_surface = "surf-1"\n', encoding="utf-8")
    sender = FakePaneSender()
    registry = ModRegistry(ModDiscovery(ModConfigLoader()), [tmp_path],
                           BoardRepository(FrontMatterParser(), BoardBuilder()),
                           AnswerStore())
    routes = MessagesRoutes(registry, MessageWriter(),
                            pane_registry=PaneRegistry(tmp_path / PANE_FILE),
                            pane_sender=sender, workbench_root=tmp_path / "wb")
    app = FastAPI()
    app.include_router(routes.routes)
    client = TestClient(app)
    response = client.post("/api/messages", json={"text": "hi", "context": {"view": "home"}})
    assert response.status_code == 200
    assert (tmp_path / "wb" / "messages" / f"{response.json()['id']}.md").exists()
    assert sender.lines[0].startswith(
        f"[workbench] mod=workbench view=home id={response.json()['id']} | hi | Reply in the workbench UI")
    assert len(client.get("/api/messages").json()["messages"]) == 1


def test_panes_route_and_targeted_message_reach_mod_pane(tmp_path: Path) -> None:
    make_mod_repo(tmp_path)
    other_repo = make_other_repo(tmp_path)
    (other_repo / "status" / "planner.toml").write_text(
        'wmux_surface = "surf-2"\n', encoding="utf-8")
    sender = FakePaneSender()
    client = panes_client(tmp_path, sender)
    assert client.get("/api/panes").json()["panes"] == [
        {"name": "planner", "mod": "OtherMod", "active_at": ""}]
    response = client.post("/api/messages", json={
        "text": "hi", "context": {"view": "home"}, "target": "planner"})
    assert response.status_code == 200
    assert response.json()["delivered"] is True
    assert sender.lines[0].startswith("[workbench] mod=OtherMod view=home id=")
    assert (other_repo / "messages").exists()
    assert client.post("/api/messages", json={
        "text": "hi", "context": {"view": "home"},
        "target": "nope"}).status_code == 404


def test_panes_route_returns_active_at_from_status_file(tmp_path: Path) -> None:
    make_mod_repo(tmp_path)
    other_repo = make_other_repo(tmp_path)
    (other_repo / "status" / "planner.toml").write_text(
        'wmux_surface = "surf-2"\n'
        'activity_at = "2026-11-12T20:43:48+00:00"\n', encoding="utf-8")
    (other_repo / "status" / "reviewer.toml").write_text(
        'wmux_surface = "surf-3"\n', encoding="utf-8")
    client = panes_client(tmp_path, FakePaneSender())
    assert client.get("/api/panes").json()["panes"] == [
        {"name": "planner", "mod": "OtherMod",
         "active_at": "2026-11-12T20:43:48+00:00"},
        {"name": "reviewer", "mod": "OtherMod", "active_at": ""}]
