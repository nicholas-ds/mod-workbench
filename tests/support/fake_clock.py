"""Shared fake clock."""


class FakeClock:
    """Return a moveable millisecond value."""

    def __init__(self, start_ms: int = 1_000_000) -> None:
        self.now_ms = start_ms

    def __call__(self) -> int:
        return self.now_ms

    def advance(self, seconds: float) -> None:
        self.now_ms += int(seconds * 1000)
