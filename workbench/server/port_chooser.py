"""Pick the serve port from the flag, then the env var, then the default."""

from __future__ import annotations


class BadPortError(ValueError):
    """The requested port is not an integer from 1 to 65535."""


class PortChooser:
    """Pick the serve port from the flag, then the env var, then the default."""

    def __init__(self, default: int) -> None:
        self._default = default

    def choose(self, argv_port: str | None, env_port: str | None) -> int:
        requested = argv_port if argv_port is not None else env_port
        if requested is None:
            return self._default
        return self._validated(requested)

    def _validated(self, raw: str) -> int:
        try:
            port = int(raw)
        except ValueError:
            raise BadPortError(f"port must be an integer, got {raw!r}") from None
        if not 1 <= port <= 65535:
            raise BadPortError(f"port must be between 1 and 65535, got {port}")
        return port
