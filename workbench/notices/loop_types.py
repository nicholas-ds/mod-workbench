"""Pure state types for the notice delivery loop."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from workbench.notices.notice_types import DeliveryRecord, Notice


class LoopStage(Enum):
    """Where a notice stands in its loop after delivery."""

    SENDING = "sending"
    GOT_IT = "got_it"
    WORKING = "working"
    DONE = "done"
    STUCK = "stuck"


@dataclass(frozen=True)
class OwnerSignal:
    """What the owner reports about a taken prompt. Empty string when missing."""

    prompt_notice: str = ""
    prompt_at: str = ""
    activity: str = ""
    activity_at: str = ""
    last_tool: str = ""
    last_tool_at: str = ""
    phase: str = ""
    summary: str = ""


@dataclass(frozen=True)
class StallLimits:
    """Quiet periods, in seconds, after which a loop counts as stuck."""

    not_seen_seconds: int = 180
    quiet_seconds: int = 600
    retry_limit: int = 5


@dataclass(frozen=True)
class LoopInputs:
    """Everything the stage deriver needs, nothing more."""

    record: DeliveryRecord
    notice: Notice
    signal: OwnerSignal | None
    new_board_since: bool
    now: datetime


@dataclass(frozen=True)
class LoopSnapshot:
    """The derived state of one notice's loop."""

    notice_id: str
    board: str
    owner: str
    stage: LoopStage
    reason: str
    since: str
    last_action: str
    summary: str
    can_retry: bool
