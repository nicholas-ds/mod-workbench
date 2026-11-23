"""Route tests for the GET chat session: id, folder, running and backend."""

from pathlib import Path

from routes_chat_fakes import make_chat_client


def test_get_session_returns_the_current_id(tmp_path: Path) -> None:
    client, fakes, _ = make_chat_client(tmp_path)
    fakes["claude"].session_ids["main"] = "ses-7"
    response = client.get("/api/chat/main/session")
    assert response.status_code == 200
    assert response.json() == {"session_id": "ses-7", "folder": "E:/m",
                               "running": False, "context_percent": 42.5,
                               "backend": "claude"}
    assert fakes["claude"].session_calls == ["main"]


def test_get_session_returns_the_folder_of_the_chat(tmp_path: Path) -> None:
    client, fakes, _ = make_chat_client(tmp_path)
    fakes["claude"].session_ids["Logistics"] = "ses-7"
    response = client.get("/api/chat/Logistics/session")
    assert response.status_code == 200
    assert response.json() == {"session_id": "ses-7", "folder": "E:/l",
                               "running": False, "context_percent": 42.5,
                               "backend": "claude"}
    assert fakes["claude"].session_calls == ["Logistics"]


def test_get_session_for_unknown_name_answers_404(tmp_path: Path) -> None:
    client, fakes, _ = make_chat_client(tmp_path)
    response = client.get("/api/chat/missing/session")
    assert response.status_code == 404
    assert fakes["claude"].session_calls == []


def test_session_id_changes_between_calls_when_the_store_changes(
        tmp_path: Path) -> None:
    client, fakes, _ = make_chat_client(tmp_path)
    fakes["claude"].session_ids["main"] = "ses-1"
    first = client.get("/api/chat/main/session")
    assert first.json()["session_id"] == "ses-1"
    fakes["claude"].session_ids["main"] = "ses-2"
    second = client.get("/api/chat/main/session")
    assert second.json()["session_id"] == "ses-2"
    assert fakes["claude"].session_calls == ["main", "main"]


def test_session_reports_running_when_the_backend_says_so(tmp_path: Path) -> None:
    client, fakes, _ = make_chat_client(tmp_path)
    fakes["claude"].running_names.add("main")
    response = client.get("/api/chat/main/session")
    assert response.status_code == 200
    assert response.json()["running"] is True
    assert fakes["claude"].is_running_calls == ["main"]


def test_session_reports_not_running_when_the_backend_is_idle(
        tmp_path: Path) -> None:
    client, fakes, _ = make_chat_client(tmp_path)
    response = client.get("/api/chat/main/session")
    assert response.status_code == 200
    assert response.json()["running"] is False
    assert fakes["claude"].is_running_calls == ["main"]


def test_session_reports_backend_and_matching_session(tmp_path: Path) -> None:
    client, fakes, _ = make_chat_client(tmp_path, {"main": "opencode"})
    fakes["opencode"].context_percent = None
    response = client.get("/api/chat/main/session")
    assert response.status_code == 200
    assert response.json() == {"session_id": "ses_opencode", "folder": "E:/m",
                               "running": False, "context_percent": None,
                               "backend": "opencode"}


def test_session_defaults_to_the_claude_backend(tmp_path: Path) -> None:
    client, _, _ = make_chat_client(tmp_path)
    response = client.get("/api/chat/main/session")
    assert response.json()["backend"] == "claude"
