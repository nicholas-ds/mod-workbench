"""The per-owner inbox of notice delivery records."""

from __future__ import annotations

import json
import os
from pathlib import Path

from workbench.notices.loop_types import LoopSnapshot, LoopStage
from workbench.notices.notice_types import DeliveryRecord, DeliveryState, Notice
from workbench.notices.owner_id import OwnerId

_OPEN_STATES = (DeliveryState.PENDING, DeliveryState.FAILED)


class OwnerInbox:
    """Notice records as JSON files, written before any send attempt."""

    def __init__(self, root: Path) -> None:
        self._root = root

    @classmethod
    def of_mod(cls, repo: Path) -> OwnerInbox:
        """The inbox of the mod whose repository is `repo`."""
        return cls(repo / "status" / "inbox")

    def write(self, notice: Notice, resolution_known: bool) -> DeliveryRecord:
        """Store the notice with a fresh record and return that record."""
        state = DeliveryState.PENDING if resolution_known else DeliveryState.UNKNOWN_OWNER
        record = DeliveryRecord(notice_id=notice.id, owner=notice.owner, state=state,
                                attempts=0, last_try="", error="")
        self._store(notice, record)
        return record

    def update(self, record: DeliveryRecord) -> None:
        """Rewrite the record part of the stored notice file."""
        path = self._path(record.owner, record.notice_id)
        payload = self._load(path)
        payload["record"] = {**vars(record), "owner": record.owner.text(),
                             "state": record.state.value}
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(payload), encoding="utf-8")
        os.replace(temp, path)

    def update_loop(self, record: DeliveryRecord, snapshot: LoopSnapshot) -> None:
        """Write the loop snapshot into the stored notice file, atomically."""
        path = self._path(record.owner, record.notice_id)
        payload = self._load(path)
        payload["loop"] = {**vars(snapshot), "stage": snapshot.stage.value}
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(payload), encoding="utf-8")
        os.replace(temp, path)

    def mark_pinged(self, record: DeliveryRecord) -> None:
        """Set the pinged flag in the stored notice file, atomically."""
        path = self._path(record.owner, record.notice_id)
        payload = self._load(path)
        payload["pinged"] = True
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(payload), encoding="utf-8")
        os.replace(temp, path)

    def was_pinged(self, record: DeliveryRecord) -> bool:
        """True when the stored notice file carries a true pinged flag."""
        payload = self._load(self._path(record.owner, record.notice_id))
        return payload.get("pinged") is True

    def notice_of(self, record: DeliveryRecord) -> Notice | None:
        """Return the stored Notice of that record, None when missing."""
        payload = self._load(self._path(record.owner, record.notice_id))
        return self._notice(payload.get("notice"))

    def loop_of(self, record: DeliveryRecord) -> LoopSnapshot | None:
        """Return the stored loop snapshot of that record, None when missing or invalid."""
        payload = self._load(self._path(record.owner, record.notice_id))
        return self._loop(payload.get("loop"))

    def list_records(self, owner: OwnerId) -> list[DeliveryRecord]:
        """Return the owner's records, newest first."""
        return self._sorted_entries(f"{self._name(owner)}/*.json")

    def all_records(self) -> list[DeliveryRecord]:
        """Return every record across all owners, newest first."""
        return self._sorted_entries("*/*.json")

    def pending(self) -> list[DeliveryRecord]:
        """Return every PENDING or FAILED record across owners, newest first."""
        records = self._sorted_entries("*/*.json")
        return [record for record in records if record.state in _OPEN_STATES]

    def _sorted_entries(self, pattern: str) -> list[DeliveryRecord]:
        entries: list[tuple[str, DeliveryRecord]] = []
        for path in sorted(self._root.glob(pattern)):
            payload = self._load(path)
            record = self._record(payload.get("record"))
            if record is not None:
                entries.append((str(payload.get("created", "")), record))
        entries.sort(key=lambda entry: entry[0], reverse=True)
        return [record for _created, record in entries]

    def _store(self, notice: Notice, record: DeliveryRecord) -> None:
        path = self._path(notice.owner, notice.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"created": notice.created,
                   "notice": {**vars(notice), "owner": notice.owner.text()},
                   "record": {**vars(record), "owner": record.owner.text(),
                              "state": record.state.value}}
        temp = path.with_suffix(".tmp")
        temp.write_text(json.dumps(payload), encoding="utf-8")
        os.replace(temp, path)

    def _path(self, owner: OwnerId, notice_id: str) -> Path:
        return self._root / self._name(owner) / f"{notice_id}.json"

    @staticmethod
    def _name(owner: OwnerId) -> str:
        return owner.text().replace(":", "_").replace("~", "_")

    @staticmethod
    def _load(path: Path) -> dict[str, object]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _record(data: object) -> DeliveryRecord | None:
        source: dict[str, object] = data if isinstance(data, dict) else {}
        try:
            return DeliveryRecord(notice_id=str(source["notice_id"]),
                                  owner=OwnerId.parse(str(source["owner"])),
                                  state=DeliveryState(str(source["state"])),
                                  attempts=int(source["attempts"]),
                                  last_try=str(source["last_try"]), error=str(source["error"]))
        except (ValueError, KeyError, TypeError):
            return None

    @staticmethod
    def _loop(data: object) -> LoopSnapshot | None:
        source: dict[str, object] = data if isinstance(data, dict) else {}
        try:
            return LoopSnapshot(notice_id=str(source["notice_id"]),
                                board=str(source["board"]), owner=str(source["owner"]),
                                stage=LoopStage(str(source["stage"])),
                                reason=str(source["reason"]), since=str(source["since"]),
                                last_action=str(source["last_action"]),
                                summary=str(source["summary"]),
                                can_retry=bool(source["can_retry"]))
        except (ValueError, KeyError, TypeError):
            return None

    @staticmethod
    def _notice(data: object) -> Notice | None:
        source: dict[str, object] = data if isinstance(data, dict) else {}
        try:
            return Notice(id=str(source["id"]),
                          owner=OwnerId.parse(str(source["owner"])),
                          board=str(source["board"]), event=str(source["event"]),
                          file_path=str(source["file_path"]), line=str(source["line"]),
                          created=str(source["created"]))
        except (ValueError, KeyError, TypeError):
            return None
