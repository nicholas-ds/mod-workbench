"""Tests for DeliveryView and DeliveryViewBuilder."""

from workbench.notices.delivery_view import DeliveryViewBuilder
from workbench.notices.notice_types import DeliveryRecord, DeliveryState
from workbench.notices.owner_id import OwnerId, OwnerKind


def _record(state: DeliveryState) -> DeliveryRecord:
    return DeliveryRecord(notice_id="n1", owner=OwnerId(OwnerKind.PANE, "boards-1"),
                          state=state, attempts=2, last_try="2026-11-23T10:00:00",
                          error="boom")


def test_view_carries_owner_text_state_and_numbers() -> None:
    view = DeliveryViewBuilder().build(_record(DeliveryState.FAILED), "storehouse")

    assert view.notice_id == "n1"
    assert view.owner == "pane:boards-1"
    assert view.state == "failed"
    assert view.attempts == 2
    assert view.last_try == "2026-11-23T10:00:00"
    assert view.error == "boom"
    assert view.board == "storehouse"


def test_labels_cover_every_state() -> None:
    build = DeliveryViewBuilder().build

    assert build(_record(DeliveryState.DELIVERED), "b").label == "Delivered"
    assert build(_record(DeliveryState.FRESH_STARTED), "b").label == "Started a fresh session"
    assert build(_record(DeliveryState.PENDING), "b").label == "Waiting to deliver"
    assert build(_record(DeliveryState.FAILED), "b").label == "Not delivered"
    assert build(_record(DeliveryState.UNKNOWN_OWNER), "b").label == "Sent to a new session in the repo"


def test_as_json_carries_every_field() -> None:
    view = DeliveryViewBuilder().build(_record(DeliveryState.FAILED), "storehouse")

    assert view.as_json() == {"notice_id": "n1", "board": "storehouse", "owner": "pane:boards-1",
                              "state": "failed", "attempts": 2,
                              "last_try": "2026-11-23T10:00:00", "error": "boom",
                              "label": "Not delivered"}
