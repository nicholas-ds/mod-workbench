"""Tests for OpencodeHttpClient, all against httpx.MockTransport (no server)."""

import base64
import json
from collections.abc import Callable

import httpx
import pytest

from workbench.opencode.opencode_http_client import OpencodeHttpClient

_PASSWORD = "pw"
_AUTH = "Basic " + base64.b64encode(f"opencode:{_PASSWORD}".encode()).decode()

Handler = Callable[[httpx.Request], httpx.Response]


def _make_client(handler: Handler) -> OpencodeHttpClient:
    client = OpencodeHttpClient("http://127.0.0.1:55125", _PASSWORD)
    client._transport = httpx.MockTransport(handler)
    return client


async def test_create_session_posts_title_model_and_location() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        payload = {"id": "ses_new", "location": {"directory": "E:/repos/mods"}}
        return httpx.Response(200, json={"data": payload})

    client = _make_client(handler)
    await client.connect()
    try:
        session_id = await client.create_session("demo", "E:/repos/mods")
    finally:
        await client.close()

    assert len(seen) == 1
    request = seen[0]
    assert request.method == "POST"
    assert request.url.path == "/api/session"
    assert request.headers["authorization"] == _AUTH
    assert json.loads(request.content) == {
        "title": "demo",
        "model": {"providerID": "zai-coding-plan", "id": "glm-5.3-flash"},
        "location": {"directory": "E:/repos/mods"},
    }
    assert session_id == "ses_new"


async def test_prompt_posts_text_to_session_path() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"data": {}})

    client = _make_client(handler)
    await client.connect()
    try:
        await client.prompt("ses_1", "hello")
    finally:
        await client.close()

    request = seen[0]
    assert request.method == "POST"
    assert request.url.path == "/api/session/ses_1/prompt"
    assert request.headers["authorization"] == _AUTH
    assert json.loads(request.content) == {"text": "hello"}


async def test_add_synthetic_posts_text_to_synthetic_path() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"data": True})

    client = _make_client(handler)
    await client.connect()
    try:
        await client.add_synthetic("ses_1", "context block")
    finally:
        await client.close()

    request = seen[0]
    assert request.method == "POST"
    assert request.url.path == "/api/session/ses_1/synthetic"
    assert request.headers["authorization"] == _AUTH
    assert json.loads(request.content) == {"text": "context block"}


async def test_connect_error_raises_oserror() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = _make_client(handler)
    await client.connect()
    try:
        with pytest.raises(OSError) as exc_info:
            await client.prompt("ses_1", "hi")
    finally:
        await client.close()

    assert "connection refused" in str(exc_info.value)


async def test_interrupt_posts_to_session_path_with_no_body() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"data": {}})

    client = _make_client(handler)
    await client.connect()
    try:
        await client.interrupt("ses_1")
    finally:
        await client.close()

    request = seen[0]
    assert request.method == "POST"
    assert request.url.path == "/api/session/ses_1/interrupt"
    assert request.headers["authorization"] == _AUTH
    assert request.content == b""


async def test_delete_session_sends_delete_to_session_path() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"data": True})

    client = _make_client(handler)
    await client.connect()
    try:
        await client.delete_session("ses_1")
    finally:
        await client.close()

    request = seen[0]
    assert request.method == "DELETE"
    assert request.url.path == "/api/session/ses_1"
    assert request.headers["authorization"] == _AUTH


async def test_messages_returns_unwrapped_list_newest_first() -> None:
    newest_first = [{"id": "msg_2"}, {"id": "msg_1"}]

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/api/session/ses_1/message"
        return httpx.Response(200, json={"data": newest_first})

    client = _make_client(handler)
    await client.connect()
    try:
        messages = await client.messages("ses_1")
    finally:
        await client.close()

    assert messages == [{"id": "msg_2"}, {"id": "msg_1"}]


async def test_is_active_checks_key_membership() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/api/session/active"
        return httpx.Response(200, json={"data": {"ses_1": {"type": "running"}}})

    client = _make_client(handler)
    await client.connect()
    try:
        assert await client.is_active("ses_1") is True
        assert await client.is_active("ses_9") is False
    finally:
        await client.close()


async def test_permission_requests_filters_by_session_id() -> None:
    seen: list[httpx.Request] = []
    pending = [
        {"id": "r1", "sessionID": "ses_1", "action": "edit", "resources": ["a"]},
        {"id": "r2", "sessionID": "ses_2", "action": "bash", "resources": ["ls"]},
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"data": pending})

    client = _make_client(handler)
    await client.connect()
    try:
        requests_for_session = await client.permission_requests("ses_1")
    finally:
        await client.close()

    assert seen[0].url.path == "/api/permission/request"
    assert requests_for_session == [
        {"id": "r1", "sessionID": "ses_1", "action": "edit", "resources": ["a"]}
    ]


async def test_answer_permission_sends_once_when_allowed() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"data": {}})

    client = _make_client(handler)
    await client.connect()
    try:
        await client.answer_permission("ses_1", "r1", allow=True)
        await client.answer_permission("ses_1", "r2", allow=False)
    finally:
        await client.close()

    assert seen[0].url.path == "/api/session/ses_1/permission/r1/reply"
    assert json.loads(seen[0].content) == {"decision": "once"}
    assert seen[1].url.path == "/api/session/ses_1/permission/r2/reply"
    assert json.loads(seen[1].content) == {"decision": "reject"}


async def test_500_raises_oserror_with_status_and_path() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    client = _make_client(handler)
    await client.connect()
    try:
        with pytest.raises(OSError) as exc_info:
            await client.prompt("ses_1", "hi")
    finally:
        await client.close()

    message = str(exc_info.value)
    assert "500" in message
    assert "/api/session/ses_1/prompt" in message


async def test_empty_body_returns_none() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(204)

    client = _make_client(handler)
    await client.connect()
    try:
        assert await client.interrupt("ses_1") is None
        assert await client.prompt("ses_1", "hi") is None
    finally:
        await client.close()


async def test_body_without_data_envelope_returns_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})

    client = _make_client(handler)
    await client.connect()
    try:
        assert await client.prompt("ses_1", "hi") is None
        assert await client.interrupt("ses_1") is None
    finally:
        await client.close()
