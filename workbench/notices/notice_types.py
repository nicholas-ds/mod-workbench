"""Value objects for notices and their delivery records."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from workbench.notices.owner_id import OwnerId


class Route(Enum):
    """How a notice reaches its owner."""

    SEND = "send"
    FRESH = "fresh"


class DeliveryState(Enum):
    """Where a notice stands in the delivery pipeline."""

    PENDING = "pending"
    DELIVERED = "delivered"
    FRESH_STARTED = "fresh_started"
    FAILED = "failed"
    UNKNOWN_OWNER = "unknown_owner"


@dataclass(frozen=True)
class Notice:
    """One board event bound to its owner."""

    id: str
    owner: OwnerId
    board: str
    event: str
    file_path: str
    line: str
    created: str


@dataclass(frozen=True)
class DeliveryRecord:
    """Outcome of one delivery attempt series."""

    notice_id: str
    owner: OwnerId
    state: DeliveryState
    attempts: int
    last_try: str
    error: str
