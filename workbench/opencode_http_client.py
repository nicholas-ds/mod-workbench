"""HTTP transport to a running OpenCode 2.3.0 server.

Pure transport: every method maps to one route, unwraps the {"data": ...}
envelope and returns the payload. No server start, no chat logic.
"""

from __future__ import annotations

from typing import Any, cast

import httpx

_MODEL = {"providerID": "zai-coding-plan", "id": "glm-5.3-flash"}


class OpencodeHttpClient:
    """One AsyncClient per instance; created in connect(), closed in close()."""

    def __init__(self, base_url: str, password: str) -> None:
        self._base_url = base_url
        self._password = password
        self._client: httpx.AsyncClient | None = None
        # Test seam: tests set this to an httpx.MockTransport before connect().
        self._transport: httpx.AsyncBaseTransport | None = None

    async def connect(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            auth=("opencode", self._password),
            transport=self._transport,
        )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def create_session(self, title: str, directory: str) -> str:
        body = {"title": title, "model": _MODEL, "location": {"directory": directory}}
        data = cast(dict[str, Any], await self._call("POST", "/session", body))
        return str(data["id"])

    async def prompt(self, session_id: str, text: str) -> None:
        await self._call("POST", f"/session/{session_id}/prompt", {"text": text})

    async def interrupt(self, session_id: str) -> None:
        await self._call("POST", f"/session/{session_id}/interrupt", None)

    async def add_synthetic(self, session_id: str, text: str) -> None:
        await self._call("POST", f"/session/{session_id}/synthetic", {"text": text})

    async def delete_session(self, session_id: str) -> None:
        await self._call("DELETE", f"/session/{session_id}", None)

    async def messages(self, session_id: str) -> list[dict]:
        path = f"/session/{session_id}/message"
        return cast(list[dict], await self._call("GET", path, None))

    async def is_active(self, session_id: str) -> bool:
        data = cast(dict, await self._call("GET", "/session/active", None))
        return session_id in data

    async def permission_requests(self, session_id: str) -> list[dict]:
        pending = cast(list[dict], await self._call("GET", "/permission/request", None))
        return [item for item in pending if item.get("sessionID") == session_id]

    async def answer_permission(
        self, session_id: str, request_id: str, allow: bool
    ) -> None:
        decision = "once" if allow else "reject"
        path = f"/session/{session_id}/permission/{request_id}/reply"
        await self._call("POST", path, {"decision": decision})

    async def _call(self, method: str, path: str, body: dict | None) -> object:
        """Send one request; raise OSError with status and path on non-2xx."""
        if self._client is None:
            raise OSError("not connected: call connect() first")
        try:
            response = await self._client.request(method, path, json=body)
        except httpx.HTTPError as exc:
            raise OSError(str(exc)) from exc
        if not 200 <= response.status_code < 300:
            raise OSError(
                f"{method} {path} failed with HTTP {response.status_code}"
            )
        if not response.content:
            return None
        payload = response.json()
        if isinstance(payload, dict) and "data" in payload:
            return payload["data"]
        return payload
