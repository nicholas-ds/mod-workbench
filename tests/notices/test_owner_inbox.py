"""Tests for OwnerInbox: write, update, list and pending records."""

from pathlib import Path

from workbench.notices.notice_types import DeliveryRecord, DeliveryState, Notice
from workbench.notices.owner_id import OwnerId, OwnerKind
from workbench.notices.owner_inbox import OwnerInbox


def _notice(notice_id: str, created: str) -> Notice:
    owner = OwnerId(OwnerKind.PANE, "boards-1")
    return Notice(id=notice_id, owner=owner, board="b1", event="answer",
                  file_path="boards/open/b1/board.md", line="hello", created=created)


def test_write_creates_file_before_any_send(tmp_path: Path) -> None:
    inbox = OwnerInbox(tmp_path)

    record = inbox.write(_notice("n1", "2026-11-23T10:00:00"), resolution_known=True)

    assert (tmp_path / "pane_boards-1" / "n1.json").exists()
    assert record.state is DeliveryState.PENDING
    assert record.attempts == 0


def test_write_marks_unknown_owner_state(tmp_path: Path) -> None:
    inbox = OwnerInbox(tmp_path)

    record = inbox.write(_notice("n1", "2026-11-23T10:00:00"), resolution_known=False)

    assert record.state is DeliveryState.UNKNOWN_OWNER


def test_write_round_trips_enums_and_owner(tmp_path: Path) -> None:
    inbox = OwnerInbox(tmp_path)
    notice = _notice("n1", "2026-11-23T10:00:00")

    record = inbox.write(notice, resolution_known=True)

    assert inbox.list_records(notice.owner) == [record]


def test_update_rewrites_the_record_part(tmp_path: Path) -> None:
    inbox = OwnerInbox(tmp_path)
    notice = _notice("n1", "2026-11-23T10:00:00")
    record = inbox.write(notice, resolution_known=True)
    updated = DeliveryRecord(notice_id=record.notice_id, owner=record.owner,
                             state=DeliveryState.DELIVERED, attempts=1,
                             last_try="2026-11-23T10:01:00", error="")

    inbox.update(updated)

    assert inbox.list_records(notice.owner) == [updated]


def test_notice_of_returns_the_stored_notice(tmp_path: Path) -> None:
    inbox = OwnerInbox(tmp_path)
    notice = _notice("n1", "2026-11-23T10:00:00")

    record = inbox.write(notice, resolution_known=True)

    assert inbox.notice_of(record) == notice


def test_notice_of_returns_none_when_file_is_missing(tmp_path: Path) -> None:
    inbox = OwnerInbox(tmp_path)
    ghost = DeliveryRecord(notice_id="ghost", owner=OwnerId(OwnerKind.PANE, "boards-1"),
                           state=DeliveryState.PENDING, attempts=0, last_try="",
                           error="")

    assert inbox.notice_of(ghost) is None


def test_list_records_orders_newest_first(tmp_path: Path) -> None:
    inbox = OwnerInbox(tmp_path)
    owner = OwnerId(OwnerKind.PANE, "boards-1")
    inbox.write(_notice("n1", "2026-11-23T09:00:00"), True)
    inbox.write(_notice("n2", "2026-11-23T10:00:00"), True)

    records = inbox.list_records(owner)

    assert [record.notice_id for record in records] == ["n2", "n1"]


def test_pending_lists_failed_and_skips_delivered(tmp_path: Path) -> None:
    inbox = OwnerInbox(tmp_path)
    first = inbox.write(_notice("n1", "2026-11-23T09:00:00"), True)
    other = Notice(id="n2", owner=OwnerId(OwnerKind.CHAT, "review"), board="b2",
                   event="answer", file_path="p", line="l", created="2026-11-23T09:30:00")
    record = inbox.write(other, True)
    inbox.update(DeliveryRecord(notice_id="n2", owner=record.owner,
                                state=DeliveryState.DELIVERED, attempts=1,
                                last_try="2026-11-23T10:00:00", error=""))
    failed = DeliveryRecord(notice_id="n1", owner=first.owner,
                            state=DeliveryState.FAILED, attempts=2,
                            last_try="2026-11-23T10:05:00", error="boom")
    inbox.update(failed)

    assert inbox.pending() == [failed]


def test_all_records_spans_owners_newest_first(tmp_path: Path) -> None:
    inbox = OwnerInbox(tmp_path)
    inbox.write(_notice("n1", "2026-11-23T09:00:00"), True)
    other = Notice(id="n2", owner=OwnerId(OwnerKind.CHAT, "review"), board="b2",
                   event="answer", file_path="p", line="l", created="2026-11-23T10:00:00")
    inbox.write(other, True)

    records = inbox.all_records()

    assert [record.notice_id for record in records] == ["n2", "n1"]
