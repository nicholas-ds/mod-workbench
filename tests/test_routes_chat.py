"""Route tests for ChatRoutes: SSE turns, stop, history and the backend flip."""

from pathlib import Path

from workbench.chat_backend_store import ChatBackendStore
from workbench.chat_event import ChatEvent
from workbench.slash_command_lister import SlashCommandInfo
from workbench.thread_registry import ChatThread

from routes_chat_fakes import (
    STORE_FILE,
    ThreadDirectory,
    make_chat_client,
    make_resolver,
    sse_events,
    thread_registry,
)


def test_post_chat_streams_events_as_sse(tmp_path: Path) -> None:
    client, _, _ = make_chat_client(tmp_path)
    response = client.post("/api/chat/main", json={"text": "hi"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert sse_events(response.text) == [
        {"kind": "text", "text": "claude hello", "tool_name": "", "detail": ""},
        {"kind": "result", "text": "done", "tool_name": "", "detail": ""},
    ]


def test_chat_accepts_a_mod_orchestrator_name(tmp_path: Path) -> None:
    client, fakes, _ = make_chat_client(tmp_path)
    response = client.post("/api/chat/Logistics", json={"text": "hi"})
    assert response.status_code == 200
    assert len(fakes["claude"].turns) == 1


def test_post_chat_passes_prompt_text_to_backend(tmp_path: Path) -> None:
    client, fakes, _ = make_chat_client(tmp_path)
    client.post("/api/chat/main", json={"text": "  build the deck  "})
    assert fakes["claude"].turns == [("main", "build the deck")]


def test_clear_text_retires_the_chat_and_answers_a_notice(tmp_path: Path) -> None:
    client, fakes, _ = make_chat_client(tmp_path)
    response = client.post("/api/chat/main", json={"text": "/clear"})
    assert sse_events(response.text) == [
        {"kind": "notice", "text": "Chat cleared.", "tool_name": "", "detail": ""}]
    assert fakes["claude"].retired == ["main"]


def test_blank_text_answers_400(tmp_path: Path) -> None:
    client, fakes, _ = make_chat_client(tmp_path)
    response = client.post("/api/chat/main", json={"text": "   "})
    assert response.status_code == 400
    assert fakes["claude"].turns == []


def test_missing_text_answers_400(tmp_path: Path) -> None:
    client, _, _ = make_chat_client(tmp_path)
    missing = client.post("/api/chat/main", json={})
    non_string = client.post("/api/chat/main", json={"text": 5})
    assert missing.status_code == 400
    assert non_string.status_code == 400


def test_unknown_name_answers_404(tmp_path: Path) -> None:
    client, fakes, _ = make_chat_client(tmp_path)
    response = client.post("/api/chat/other", json={"text": "hi"})
    assert response.status_code == 404
    assert fakes["claude"].turns == []


def test_stop_calls_backend_and_answers_ok(tmp_path: Path) -> None:
    client, fakes, _ = make_chat_client(tmp_path)
    response = client.post("/api/chat/main/stop")
    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert fakes["claude"].stop_calls == ["main"]


def test_stop_unknown_name_answers_404(tmp_path: Path) -> None:
    client, fakes, _ = make_chat_client(tmp_path)
    response = client.post("/api/chat/other/stop")
    assert response.status_code == 404
    assert fakes["claude"].stop_calls == []


def test_history_returns_saved_events_for_a_known_name(tmp_path: Path) -> None:
    client, fakes, _ = make_chat_client(tmp_path)
    fakes["claude"].history_events = (ChatEvent(kind="text", text="old"),)
    response = client.get("/api/chat/main/history")
    assert response.status_code == 200
    assert fakes["claude"].history_calls == ["main"]
    assert response.json() == {"events": [
        {"kind": "text", "text": "old", "tool_name": "", "detail": ""}]}


def test_history_unknown_name_answers_404(tmp_path: Path) -> None:
    client, fakes, _ = make_chat_client(tmp_path)
    response = client.get("/api/chat/other/history")
    assert response.status_code == 404
    assert fakes["claude"].history_calls == []


def test_backend_route_saves_for_a_bare_name(tmp_path: Path) -> None:
    client, _, _ = make_chat_client(tmp_path)
    response = client.post("/api/chat/main/backend", json={"backend": "opencode"})
    assert response.status_code == 200
    assert response.json() == {"ok": True, "backend": "opencode"}
    assert ChatBackendStore(tmp_path / STORE_FILE).load("main") == "opencode"


def test_backend_route_rejects_unknown_values(tmp_path: Path) -> None:
    client, _, _ = make_chat_client(tmp_path)
    glm = client.post("/api/chat/main/backend", json={"backend": "glm"})
    missing = client.post("/api/chat/main/backend", json={})
    number = client.post("/api/chat/main/backend", json={"backend": 5})
    assert glm.status_code == 400
    assert missing.status_code == 400
    assert number.status_code == 400
    assert client.get("/api/chat/main/session").json()["backend"] == "claude"


def test_flip_refused_while_running_answers_409(tmp_path: Path) -> None:
    client, fakes, _ = make_chat_client(tmp_path)
    fakes["claude"].running_names.add("main")
    response = client.post("/api/chat/main/backend", json={"backend": "opencode"})
    assert response.status_code == 409
    assert response.json() == {"detail": "A turn is running. Stop it first."}
    assert ChatBackendStore(tmp_path / STORE_FILE).load("main") == "claude"


def test_dispatch_uses_the_opencode_backend_when_flipped(tmp_path: Path) -> None:
    client, fakes, _ = make_chat_client(tmp_path, {"main": "opencode"})
    response = client.post("/api/chat/main", json={"text": "hi"})
    assert sse_events(response.text)[0]["text"] == "opencode hello"
    assert fakes["opencode"].turns == [("main", "hi")]
    assert fakes["claude"].turns == []
    stop = client.post("/api/chat/main/stop")
    assert stop.json() == {"ok": True}
    assert fakes["opencode"].stop_calls == ["main"]
    assert fakes["claude"].stop_calls == []


def test_dispatch_keeps_the_claude_backend_by_default(tmp_path: Path) -> None:
    client, fakes, _ = make_chat_client(tmp_path)
    client.post("/api/chat/main", json={"text": "hi"})
    assert len(fakes["claude"].turns) == 1
    assert fakes["opencode"].turns == []


def test_dispatch_uses_a_thread_name_store_entry(tmp_path: Path) -> None:
    threads = thread_registry(tmp_path, "main")
    client, fakes, _ = make_chat_client(tmp_path, {"main~t1": "opencode"},
                                        threads=threads,
                                        directory=ThreadDirectory())
    client.post("/api/chat/main~t1", json={"text": "hi"})
    assert fakes["opencode"].turns == [("main~t1", "hi")]
    assert fakes["claude"].turns == []


def test_backend_post_on_thread_flips_and_dispatches(tmp_path: Path) -> None:
    threads = thread_registry(tmp_path)
    client, fakes, _ = make_chat_client(tmp_path, threads=threads,
                                        directory=ThreadDirectory())
    response = client.post("/api/chat/Workbench~t1/backend",
                           json={"backend": "opencode"})
    assert response.status_code == 200
    assert response.json() == {"ok": True, "backend": "opencode"}
    turn = client.post("/api/chat/Workbench~t1", json={"text": "hi"})
    assert sse_events(turn.text)[0]["text"] == "opencode hello"
    assert fakes["opencode"].turns == [("Workbench~t1", "hi")]


def test_flip_persists_for_a_thread_name(tmp_path: Path) -> None:
    threads = thread_registry(tmp_path)
    client, _, _ = make_chat_client(tmp_path, threads=threads,
                                    directory=ThreadDirectory())
    client.post("/api/chat/Workbench~t1/backend", json={"backend": "opencode"})
    second, _ = make_resolver(tmp_path)
    assert second.backend_of("Workbench~t1").traits.key == "opencode"
    assert second.backend_of("Workbench").traits.key == "claude"


def test_backend_post_on_bare_name_still_saves_to_store(tmp_path: Path) -> None:
    threads = thread_registry(tmp_path)
    client, _, _ = make_chat_client(tmp_path, threads=threads,
                                    directory=ThreadDirectory())
    response = client.post("/api/chat/Workbench/backend",
                           json={"backend": "opencode"})
    assert response.status_code == 200
    assert ChatBackendStore(tmp_path / STORE_FILE).load("Workbench") == "opencode"
    assert threads.list_threads("Workbench") == (
        ChatThread("Workbench", "t1", "thread 1"),)


def test_backend_post_unknown_thread_answers_404(tmp_path: Path) -> None:
    threads = thread_registry(tmp_path)
    client, _, _ = make_chat_client(tmp_path, threads=threads,
                                    directory=ThreadDirectory())
    response = client.post("/api/chat/Workbench~t9/backend",
                           json={"backend": "opencode"})
    assert response.status_code == 404
    assert ChatBackendStore(tmp_path / STORE_FILE).load("Workbench~t9") == "claude"


def test_backend_post_bad_value_on_thread_answers_400(tmp_path: Path) -> None:
    threads = thread_registry(tmp_path)
    client, _, _ = make_chat_client(tmp_path, threads=threads,
                                    directory=ThreadDirectory())
    response = client.post("/api/chat/Workbench~t1/backend",
                           json={"backend": "glm"})
    assert response.status_code == 400
    assert threads.list_threads("Workbench") == (
        ChatThread("Workbench", "t1", "thread 1"),)


def test_history_uses_the_matching_backend(tmp_path: Path) -> None:
    client, fakes, _ = make_chat_client(tmp_path, {"main": "opencode"})
    fakes["claude"].history_calls.clear()
    fakes["opencode"].history_events = (ChatEvent(kind="text", text="glm old"),)
    response = client.get("/api/chat/main/history")
    assert response.status_code == 200
    assert fakes["opencode"].history_calls == ["main"]
    assert fakes["claude"].history_calls == []
    assert response.json() == {"events": [
        {"kind": "text", "text": "glm old", "tool_name": "", "detail": ""}]}


def test_commands_come_from_the_backend_of_the_chat(tmp_path: Path) -> None:
    client, fakes, _ = make_chat_client(tmp_path, {"main": "opencode"})
    fakes["opencode"].command_rows = (
        SlashCommandInfo(name="glm-only", description="GLM row"),)
    response = client.get("/api/chat/main/commands")
    assert response.status_code == 200
    assert response.json() == {"commands": [
        {"name": "glm-only", "description": "GLM row"}]}
    assert fakes["opencode"].commands_calls == ["main"]
    assert fakes["claude"].commands_calls == []
