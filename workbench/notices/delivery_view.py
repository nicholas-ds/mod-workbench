"""Read-only view of one delivery record for the web API."""

from __future__ import annotations

from dataclasses import dataclass

from workbench.notices.notice_types import DeliveryRecord, DeliveryState

_LABELS: dict[DeliveryState, str] = {
    DeliveryState.DELIVERED: "Delivered",
    DeliveryState.FRESH_STARTED: "Started a fresh session",
    DeliveryState.PENDING: "Waiting to deliver",
    DeliveryState.FAILED: "Not delivered",
    DeliveryState.UNKNOWN_OWNER: "Sent to the default owner",
}


@dataclass(frozen=True)
class DeliveryView:
    """One delivery record as plain text, ready for JSON."""

    notice_id: str
    owner: str
    state: str
    attempts: int
    last_try: str
    error: str
    label: str

    def as_json(self) -> dict[str, object]:
        """Return the view as a JSON-ready dict."""
        return {"notice_id": self.notice_id, "owner": self.owner, "state": self.state,
                "attempts": self.attempts, "last_try": self.last_try,
                "error": self.error, "label": self.label}


class DeliveryViewBuilder:
    """Build one DeliveryView from a stored DeliveryRecord."""

    def build(self, record: DeliveryRecord) -> DeliveryView:
        """Map the record's enums to plain text and its plain-English label."""
        return DeliveryView(notice_id=record.notice_id, owner=record.owner.text(),
                            state=record.state.value, attempts=record.attempts,
                            last_try=record.last_try, error=record.error,
                            label=_LABELS[record.state])
