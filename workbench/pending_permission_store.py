"""Open permission requests: one asyncio future per request id (Task: permission prompts)."""

from __future__ import annotations

import asyncio
from uuid import uuid4


class PendingPermissionStore:
    """Hold one future per open permission request; wake its waiter on answer."""

    def __init__(self) -> None:
        self._futures: dict[str, asyncio.Future[str]] = {}

    def hold(self) -> str:
        request_id = uuid4().hex
        self._futures[request_id] = asyncio.get_running_loop().create_future()
        return request_id

    async def await_decision(self, request_id: str, timeout_seconds: float) -> str:
        future = self._futures.get(request_id)
        if future is None:
            return "denied"
        try:
            return await asyncio.wait_for(future, timeout_seconds)
        except asyncio.TimeoutError:
            return "timed out"
        finally:
            self._futures.pop(request_id, None)

    def answer(self, request_id: str, allowed: bool) -> bool:
        future = self._futures.get(request_id)
        if future is None or future.done():
            return False
        future.set_result("allowed" if allowed else "denied")
        return True

    def fail_all(self) -> None:
        for future in self._futures.values():
            if not future.done():
                future.set_result("denied")

    def open_ids(self) -> tuple[str, ...]:
        return tuple(
            request_id
            for request_id, future in self._futures.items()
            if not future.done()
        )
