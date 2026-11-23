"""The record a detached server writes so later runs can find it."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ServerRecord:
    """Identity of a running detached server, stored as JSON."""

    pid: int
    port: int
    started: str  # ISO text
