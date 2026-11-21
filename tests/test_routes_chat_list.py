"""Route tests for the chat list endpoints: orchestrators and backends."""

from pathlib import Path

from routes_chat_fakes import make_chat_client


def test_get_chat_lists_orchestrators(tmp_path: Path) -> None:
    client, _, _ = make_chat_client(tmp_path)
    response = client.get("/api/chat")
    assert response.status_code == 200
    assert response.json() == {"orchestrators": [
        {"name": "main", "folder": "E:/m", "backend": "claude"},
        {"name": "Logistics", "folder": "E:/l", "backend": "claude"},
    ]}


def test_backends_lists_both_traits(tmp_path: Path) -> None:
    client, _, _ = make_chat_client(tmp_path)
    response = client.get("/api/chat/backends")
    assert response.status_code == 200
    traits = response.json()["backends"]
    assert [row["key"] for row in traits] == ["claude", "opencode"]
    assert all("label" in row and "tab_mark" in row for row in traits)


def test_orchestrator_list_gains_the_saved_backend(tmp_path: Path) -> None:
    client, _, _ = make_chat_client(tmp_path, {"main": "opencode"})
    response = client.get("/api/chat")
    assert response.json() == {"orchestrators": [
        {"name": "main", "folder": "E:/m", "backend": "opencode"},
        {"name": "Logistics", "folder": "E:/l", "backend": "claude"},
    ]}
