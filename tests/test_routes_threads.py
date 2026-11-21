"""Route tests for chat threads: list, add, remove, and the name guards."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from workbench.routes_threads import ThreadRoutes
from workbench.thread_registry import ChatThread, ThreadRegistry

from routes_chat_fakes import make_chat_client, make_resolver


class FakeDirectory:
    """One orchestrator "main"; strips the thread suffix like the real one."""

    def folder_of(self, name: str) -> str:
        orchestrator, _ = ChatThread.split_name(name)
        return "E:/m" if orchestrator == "main" else ""


def make_client(tmp_path: Path,
                threads: ThreadRegistry) -> tuple[TestClient, dict]:
    resolver, fakes = make_resolver(tmp_path)
    routes = ThreadRoutes(FakeDirectory(), threads, resolver)
    app = FastAPI()
    app.include_router(routes.routes)
    return TestClient(app, base_url="http://127.0.0.1"), fakes


def make_chat(tmp_path: Path, threads: ThreadRegistry) -> tuple[TestClient, dict]:
    client, fakes, _ = make_chat_client(tmp_path, directory=FakeDirectory(),
                                        threads=threads)
    return client, fakes


def test_list_is_empty_for_a_fresh_orchestrator(tmp_path: Path) -> None:
    threads = ThreadRegistry(tmp_path / "threads.json")
    client, _ = make_client(tmp_path, threads)
    response = client.get("/api/chat/main/threads")
    assert response.status_code == 200
    assert response.json() == {"threads": []}


def test_add_then_list_returns_the_new_thread(tmp_path: Path) -> None:
    threads = ThreadRegistry(tmp_path / "threads.json")
    client, _ = make_client(tmp_path, threads)
    client.post("/api/chat/main/threads")
    response = client.get("/api/chat/main/threads")
    assert response.status_code == 200
    assert response.json() == {"threads": [
        {"name": "main~t1", "thread_id": "t1", "label": "thread 1", "mark": "cl"}]}


def test_add_returns_t1_then_t2(tmp_path: Path) -> None:
    threads = ThreadRegistry(tmp_path / "threads.json")
    client, _ = make_client(tmp_path, threads)
    first = client.post("/api/chat/main/threads")
    second = client.post("/api/chat/main/threads")
    assert first.json() == {"name": "main~t1", "thread_id": "t1",
                            "label": "thread 1", "mark": "cl"}
    assert second.json() == {"name": "main~t2", "thread_id": "t2",
                             "label": "thread 2", "mark": "cl"}


def test_delete_known_thread_answers_ok(tmp_path: Path) -> None:
    threads = ThreadRegistry(tmp_path / "threads.json")
    threads.add("main")
    client, _ = make_client(tmp_path, threads)
    response = client.delete("/api/chat/main/threads/t1")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert not threads.contains("main~t1")


def test_delete_unknown_thread_answers_404(tmp_path: Path) -> None:
    threads = ThreadRegistry(tmp_path / "threads.json")
    client, _ = make_client(tmp_path, threads)
    response = client.delete("/api/chat/main/threads/t9")
    assert response.status_code == 404


def test_unknown_orchestrator_answers_404(tmp_path: Path) -> None:
    threads = ThreadRegistry(tmp_path / "threads.json")
    client, _ = make_client(tmp_path, threads)
    assert client.get("/api/chat/missing/threads").status_code == 404
    assert client.post("/api/chat/missing/threads").status_code == 404


def test_thread_name_as_orchestrator_answers_404(tmp_path: Path) -> None:
    threads = ThreadRegistry(tmp_path / "threads.json")
    threads.add("main")
    client, _ = make_client(tmp_path, threads)
    assert client.get("/api/chat/main~t1/threads").status_code == 404
    assert client.post("/api/chat/main~t1/threads").status_code == 404


def test_delete_calls_forget_on_both_backends(tmp_path: Path) -> None:
    threads = ThreadRegistry(tmp_path / "threads.json")
    threads.add("main")
    client, fakes = make_client(tmp_path, threads)
    client.delete("/api/chat/main/threads/t1")
    assert fakes["claude"].retired == ["main~t1"]
    assert fakes["opencode"].retired == ["main~t1"]


def test_chat_rejects_an_unregistered_thread_name(tmp_path: Path) -> None:
    threads = ThreadRegistry(tmp_path / "threads.json")
    threads.add("main")
    client, _ = make_chat(tmp_path, threads)
    response = client.post("/api/chat/main~t9/stop")
    assert response.status_code == 404


def test_chat_allows_a_registered_thread_name(tmp_path: Path) -> None:
    threads = ThreadRegistry(tmp_path / "threads.json")
    threads.add("main")
    client, fakes = make_chat(tmp_path, threads)
    response = client.post("/api/chat/main~t1/stop")
    assert response.status_code == 200
    assert fakes["claude"].stop_calls == ["main~t1"]
