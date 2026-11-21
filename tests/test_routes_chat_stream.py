"""Route tests for the GET chat stream: SSE events of the running turn."""

from pathlib import Path

from workbench.chat_event import ChatEvent

from routes_chat_fakes import make_chat_client, sse_events


def test_get_stream_returns_running_turn_events_as_sse(tmp_path: Path) -> None:
    events = (ChatEvent(kind="text", text="live"),
              ChatEvent(kind="result", text="done"))
    client, fakes, _ = make_chat_client(tmp_path)
    fakes["claude"].follow_events = events
    response = client.get("/api/chat/main/stream")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert sse_events(response.text) == [
        {"kind": "text", "text": "live", "tool_name": "", "detail": ""},
        {"kind": "result", "text": "done", "tool_name": "", "detail": ""},
    ]
    assert fakes["claude"].follow_calls == ["main"]


def test_get_stream_for_unknown_name_answers_404(tmp_path: Path) -> None:
    client, fakes, _ = make_chat_client(tmp_path)
    response = client.get("/api/chat/missing/stream")
    assert response.status_code == 404
    assert fakes["claude"].follow_calls == []


def test_get_stream_with_no_running_turn_is_empty_200(tmp_path: Path) -> None:
    client, _, _ = make_chat_client(tmp_path)
    response = client.get("/api/chat/main/stream")
    assert response.status_code == 200
    assert response.text == ""


def test_get_stream_follows_the_flipped_backend(tmp_path: Path) -> None:
    client, fakes, _ = make_chat_client(tmp_path, {"main": "opencode"})
    response = client.get("/api/chat/main/stream")
    assert response.status_code == 200
    assert fakes["opencode"].follow_calls == ["main"]
    assert fakes["claude"].follow_calls == []
