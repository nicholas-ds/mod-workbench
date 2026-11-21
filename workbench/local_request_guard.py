"""ASGI middleware that refuses state-changing requests that a web page on another site sent.

A browser always adds an ``Origin`` header to a cross-site POST. If that origin is not this
machine, any website could drive the workbench (and the chat sessions behind it). Requests
without an ``Origin`` header (hooks, curl, tests) pass. Every request must also carry a
``Host`` header naming this machine, which stops a DNS rebinding page that reads chat history.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit

Message = dict[str, object]

_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
_REFUSAL = json.dumps({"detail": "cross-site request refused"}).encode()


class LocalRequestGuard:
    """Answer 403 to a request with a foreign Host or, when unsafe, a foreign Origin."""

    def __init__(self, app: Callable[[Message, object, object], Awaitable[None]],
                 allowed_hosts: frozenset[str] = LOCAL_HOSTS) -> None:
        self._app = app
        self._allowed_hosts = allowed_hosts

    async def __call__(self, scope: Message, receive: object,
                       send: Callable[[Message], Awaitable[None]]) -> None:
        if scope.get("type") == "http" and not self._allowed(scope):
            await self._refuse(send)
            return
        await self._app(scope, receive, send)

    def _allowed(self, scope: Message) -> bool:
        return self._host_allowed(scope) and self._origin_allowed(scope)

    def _host_allowed(self, scope: Message) -> bool:
        value = self._header(scope, b"host")
        if value is None:
            return False
        return urlsplit("//" + value).hostname in self._allowed_hosts

    def _origin_allowed(self, scope: Message) -> bool:
        if str(scope.get("method", "")).upper() in _SAFE_METHODS:
            return True
        origin = self._header(scope, b"origin")
        return origin is None or urlsplit(origin).hostname in LOCAL_HOSTS

    @staticmethod
    def _header(scope: Message, name: bytes) -> str | None:
        for header_name, value in scope.get("headers", []):
            if header_name.lower() == name:
                return value.decode("latin-1")
        return None

    @staticmethod
    async def _refuse(send: Callable[[Message], Awaitable[None]]) -> None:
        await send({"type": "http.response.start", "status": 403,
                    "headers": [(b"content-type", b"application/json")]})
        await send({"type": "http.response.body", "body": _REFUSAL})
