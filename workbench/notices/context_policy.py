"""Pick the delivery route from the owner's context usage."""

from __future__ import annotations

from workbench.notices.notice_types import Route


class ContextPolicy:
    """Send at or below the context threshold, start fresh above it."""

    def __init__(self, threshold_percent: float = 25.0) -> None:
        self._threshold_percent = threshold_percent

    def route(self, percent: float | None) -> Route:
        if percent is None or percent <= self._threshold_percent:
            return Route.SEND
        return Route.FRESH
