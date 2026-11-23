"""The base class for jobs that run for the server's whole lifespan."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BackgroundJob(ABC):
    """A background job that runs until cancelled and closes on shutdown."""

    @abstractmethod
    async def run(self) -> None:
        """Run until the task is cancelled."""

    async def close(self) -> None:
        """Release owned resources. Jobs that own resources override this."""
