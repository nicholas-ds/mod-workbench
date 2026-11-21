"""Route tests for the resume picker: GET sessions and POST resume."""

from pathlib import Path

from routes_chat_fakes import make_chat_client
from workbench.session_summary import SessionSummary


def test_sessions_returns_the_listed_rows(tmp_path: Path) -> None:
    client, fakes, _ = make_chat_client(tmp_path)
    fakes["claude"].session_rows["main"] = (
        SessionSummary(session_id="ses-1", title="First",
                       last_modified_ms=111),
        SessionSummary(session_id="ses-2", title="Second",
                       last_modified_ms=222),
    )
    response = client.get("/api/chat/main/sessions")
    assert response.status_code == 200
    assert response.json() == {"sessions": [
        {"session_id": "ses-1", "title": "First", "last_modified_ms": 111},
        {"session_id": "ses-2", "title": "Second", "last_modified_ms": 222},
    ]}
    assert fakes["claude"].sessions_calls == [("main", "E:/m")]


def test_sessions_for_unknown_name_answers_404(tmp_path: Path) -> None:
    client, fakes, _ = make_chat_client(tmp_path)
    response = client.get("/api/chat/missing/sessions")
    assert response.status_code == 404
    assert fakes["claude"].sessions_calls == []


def test_resume_switches_and_answers_ok(tmp_path: Path) -> None:
    client, fakes, _ = make_chat_client(tmp_path)
    fakes["claude"].resume_ok.add("ses-7")
    response = client.post("/api/chat/main/resume",
                           json={"session_id": "ses-7"})
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert fakes["claude"].resume_calls == [("main", "E:/m", "ses-7")]


def test_resume_refused_answers_409(tmp_path: Path) -> None:
    client, fakes, _ = make_chat_client(tmp_path)
    response = client.post("/api/chat/main/resume",
                           json={"session_id": "ses-7"})
    assert response.status_code == 409
    assert fakes["claude"].resume_calls == [("main", "E:/m", "ses-7")]


def test_resume_without_a_session_id_answers_400(tmp_path: Path) -> None:
    client, _, _ = make_chat_client(tmp_path)
    response = client.post("/api/chat/main/resume", json={})
    assert response.status_code == 400


def test_resume_with_an_empty_session_id_answers_400(tmp_path: Path) -> None:
    client, _, _ = make_chat_client(tmp_path)
    response = client.post("/api/chat/main/resume", json={"session_id": ""})
    assert response.status_code == 400
