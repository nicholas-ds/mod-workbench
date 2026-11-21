"""Route tests for UploadRoutes: POST one raw file into a chat folder."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from workbench.chat_upload_saver import ChatUploadSaver
from workbench.orchestrator_directory import OrchestratorEntry
from workbench.routes_upload import UploadRoutes


class FakeDirectory:
    """One orchestrator entry: main, mapped to a test folder."""

    def __init__(self, folder: str) -> None:
        self._entries = (OrchestratorEntry(name="main", folder=folder),)

    def entries(self) -> tuple[OrchestratorEntry, ...]:
        return self._entries

    def folder_of(self, name: str) -> str:
        for entry in self._entries:
            if entry.name == name:
                return entry.folder
        return ""


def make_client(folder: str, saver: ChatUploadSaver | None = None) -> TestClient:
    routes = UploadRoutes(FakeDirectory(folder), saver or ChatUploadSaver())
    app = FastAPI()
    app.include_router(routes.routes)
    return TestClient(app)


def test_post_raw_bytes_saves_the_file_and_returns_the_path(
        tmp_path: Path) -> None:
    client = make_client(str(tmp_path))
    response = client.post("/api/chat/main/upload?filename=notes.txt",
                           content=b"hello")
    assert response.status_code == 200
    path = response.json()["path"]
    assert path.endswith("uploads/notes.txt")
    assert (tmp_path / "uploads" / "notes.txt").read_bytes() == b"hello"


def test_unknown_name_answers_404(tmp_path: Path) -> None:
    client = make_client(str(tmp_path))
    response = client.post("/api/chat/other/upload?filename=a.txt", content=b"x")
    assert response.status_code == 404
    assert not (tmp_path / "uploads").exists()


def test_empty_body_answers_400(tmp_path: Path) -> None:
    client = make_client(str(tmp_path))
    response = client.post("/api/chat/main/upload?filename=a.txt", content=b"")
    assert response.status_code == 400


def test_content_length_over_max_bytes_answers_413_and_saves_nothing(
        tmp_path: Path) -> None:
    client = make_client(str(tmp_path), ChatUploadSaver(max_bytes=4))
    response = client.post("/api/chat/main/upload?filename=a.txt", content=b"x" * 10)
    assert response.status_code == 413
    assert not (tmp_path / "uploads").exists()
