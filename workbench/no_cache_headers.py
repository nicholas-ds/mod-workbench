"""ASGI middleware that marks non-API responses so browsers revalidate them."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

Message = dict[str, object]


class NoCacheHeaders:
    """Send ``Cache-Control: no-cache`` on every response outside ``/api/``."""

    def __init__(self, app: Callable[[Message, object, object], Awaitable[None]]) -> None:
        self._app = app

    async def __call__(self, scope: Message, receive: object,
                       send: Callable[[Message], Awaitable[None]]) -> None:
        if scope.get("type") != "http" or str(scope.get("path", "")).startswith("/api/"):
            await self._app(scope, receive, send)
            return
        await self._app(scope, receive, self._mark_no_cache(send))

    @staticmethod
    def _mark_no_cache(send: Callable[[Message], Awaitable[None]]) -> Callable[[Message], Awaitable[None]]:
        async def send_with_header(message: Message) -> None:
            if message.get("type") == "http.response.start":
                message["headers"] = NoCacheHeaders._with_header(message.get("headers", []))
            await send(message)

        return send_with_header

    @staticmethod
    def _with_header(headers: list[tuple[bytes, bytes]]) -> list[tuple[bytes, bytes]]:
        kept = [(name, value) for name, value in headers if name.lower() != b"cache-control"]
        return kept + [(b"cache-control", b"no-cache")]
