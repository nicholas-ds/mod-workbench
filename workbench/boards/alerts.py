"""Alert rules, test-report inspection and Windows toast delivery."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Protocol

from workbench.boards.board_types import BoardEntry
from workbench.boards.front_matter import FrontMatterParser
from workbench.boards.queue import BlockingRule

logger = logging.getLogger(__name__)

_FAIL_RESULT = "fail"
_APP_ID = "mod-workbench"


class ToastService(Protocol):
    """One toast sink that can be replaced in tests."""

    def send(self, title: str, message: str) -> None: ...


class AlertRules:
    """Decide which boards alert the author."""

    def __init__(self, blocking: BlockingRule | None = None) -> None:
        self._blocking = blocking if blocking is not None else BlockingRule()

    def should_alert(self, entry: BoardEntry) -> bool:
        return self._blocking.is_blocking(entry)


class NewBoardTracker:
    """Return blocking boards whose ids were not returned before."""

    def __init__(self, blocking: BlockingRule | None = None) -> None:
        self._blocking = blocking if blocking is not None else BlockingRule()
        self._seen: set[str] = set()

    def new_blocking(self, entries: list[BoardEntry]) -> list[BoardEntry]:
        fresh = [entry for entry in entries
                 if self._blocking.is_blocking(entry)
                 and entry.board.id not in self._seen]
        self._seen.update(entry.board.id for entry in fresh)
        return fresh


class ReportInspector:
    """Read one test report and tell whether it failed."""

    def __init__(self, parser: FrontMatterParser | None = None) -> None:
        self._parser = parser if parser is not None else FrontMatterParser()

    def has_failed(self, report: Path) -> bool:
        text = report.read_text(encoding="utf-8")
        front_matter = self._parser.parse(text)
        return front_matter.fields.get("result") == _FAIL_RESULT


class WinotifyService:
    """Send one toast through winotify."""

    def __init__(self, app_id: str = _APP_ID) -> None:
        self._app_id = app_id
        # Imported here so the module loads on hosts without a toast service.
        from winotify import Notification

        self._notification = Notification

    def send(self, title: str, message: str) -> None:
        self._notification(app_id=self._app_id, title=title, msg=message).show()


class ToastSourceDetector:
    """Pick the toast service on this host, or None when there is none."""

    def detect(self) -> ToastService | None:
        try:
            return WinotifyService()
        except ImportError:
            return None


class ToastNotifier:
    """Show toasts; log and continue when the toast service is missing."""

    def __init__(self, source: ToastService | None) -> None:
        self._source = source

    def notify(self, title: str, message: str) -> None:
        if self._source is None:
            logger.warning("no toast service; dropped alert: %s", title)
            return
        try:
            self._source.send(title, message)
        except Exception:
            logger.exception("toast failed; dropped alert: %s", title)


class PermissionWaitAlert:
    """Tell the author that a chat waits for a permission answer."""

    def __init__(self, notifier: ToastNotifier) -> None:
        self._notifier = notifier

    def notify(self, name: str, tool_name: str) -> None:
        self._notifier.notify(
            "Workbench: permission needed", f"{name} waits to use {tool_name}")
