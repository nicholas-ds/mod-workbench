"""Route tests for the chat permission route."""

from pathlib import Path

from fastapi.testclient import TestClient

from routes_chat_fakes import RecordingStore, make_app


def make_permission_client(tmp_path: Path,
                           result: bool = True) -> tuple[TestClient, RecordingStore]:
    store = RecordingStore(result)
    return make_app(store, tmp_path), store


def test_permission_allow_answers_the_store(tmp_path: Path) -> None:
    client, store = make_permission_client(tmp_path)
    response = client.post("/api/chat/main/permission",
                           json={"request_id": "r1", "decision": "allow"})
    assert response.status_code == 200
    assert store.calls == [("r1", True)]


def test_permission_deny_answers_the_store_with_false(tmp_path: Path) -> None:
    client, store = make_permission_client(tmp_path)
    response = client.post("/api/chat/main/permission",
                           json={"request_id": "r1", "decision": "deny"})
    assert response.status_code == 200
    assert store.calls == [("r1", False)]


def test_permission_unknown_name_is_404(tmp_path: Path) -> None:
    client, store = make_permission_client(tmp_path)
    response = client.post("/api/chat/other/permission",
                           json={"request_id": "r1", "decision": "allow"})
    assert response.status_code == 404
    assert store.calls == []


def test_permission_bad_decision_is_400(tmp_path: Path) -> None:
    client, store = make_permission_client(tmp_path)
    response = client.post("/api/chat/main/permission",
                           json={"request_id": "r1", "decision": "maybe"})
    assert response.status_code == 400
    assert store.calls == []


def test_permission_missing_request_id_is_400(tmp_path: Path) -> None:
    client, store = make_permission_client(tmp_path)
    missing = client.post("/api/chat/main/permission", json={"decision": "allow"})
    non_string = client.post("/api/chat/main/permission",
                             json={"request_id": 5, "decision": "allow"})
    assert missing.status_code == 400
    assert non_string.status_code == 400
    assert store.calls == []


def test_permission_response_reports_the_store_result(tmp_path: Path) -> None:
    allowed_client, _ = make_permission_client(tmp_path, result=True)
    denied_client, _ = make_permission_client(tmp_path, result=False)
    allowed = allowed_client.post("/api/chat/main/permission",
                                  json={"request_id": "r1", "decision": "allow"})
    denied = denied_client.post("/api/chat/main/permission",
                                json={"request_id": "r1", "decision": "allow"})
    assert allowed.json() == {"ok": True}
    assert denied.json() == {"ok": False}
