"""Tests for BoardNoticeSender: the event file path and the delivery verdict."""

from pathlib import Path

from workbench.boards.board_types import Board, BoardEntry
from workbench.core.config import ModConfig
from workbench.notices.board_notice_sender import BoardNoticeSender
from workbench.notices.notice_events import (ANSWERS_EVENT, CLOSED_EVENT,
                                             NoteNotice, REOPENED_EVENT)
from workbench.notices.notice_types import DeliveryRecord, DeliveryState
from workbench.notices.owner_id import OwnerId, OwnerKind

OWNER = OwnerId(OwnerKind.PANE, "main-orchestrator")
NOW = "2026-11-23T10:00:00"
BOARD_FOLDER = Path("boards/open/layout")
ANSWERS_PATH = str(BOARD_FOLDER / "answers.json")
NOTE_PATH = Path("notes/layout-1.md")


class FakeDispatcher:
    """Fake NoticeDispatcher that records dispatch calls and returns one record."""

    def __init__(self, state: DeliveryState) -> None:
        self._state = state
        self.calls: list[tuple[str, str, str]] = []

    def dispatch(self, board: Board, event: str, file_path: str) -> DeliveryRecord:
        self.calls.append((board.id, event, file_path))
        return DeliveryRecord(notice_id="n1", owner=OWNER, state=self._state,
                              attempts=1, last_try=NOW, error="")


class FakeFactory:
    """Fake NoticeDispatcherFactory that hands out one recorded dispatcher."""

    def __init__(self, dispatcher: FakeDispatcher) -> None:
        self._dispatcher = dispatcher
        self.built: list[str] = []

    def build(self, cfg: ModConfig) -> FakeDispatcher:
        self.built.append(cfg.name)
        return self._dispatcher


def _config(tmp_path: Path) -> ModConfig:
    return ModConfig(name="CityMod", repo=tmp_path, platform=tmp_path, screens=(),
                     boards=tmp_path / "boards", status=tmp_path / "status",
                     tracking=tmp_path, log=tmp_path, briefs=tmp_path / "briefs",
                     exports=tmp_path)


def _entry() -> BoardEntry:
    board = Board(id="layout", folder=BOARD_FOLDER, title="Queue layout")
    return BoardEntry(board=board)


def _sender(state: DeliveryState) -> tuple[BoardNoticeSender, FakeDispatcher]:
    dispatcher = FakeDispatcher(state)
    return BoardNoticeSender(FakeFactory(dispatcher)), dispatcher


def _note() -> NoteNotice:
    return NoteNotice(item="shot.png", x=0.5, y=0.25, text="look here", path=NOTE_PATH)


def test_notify_answers_on_delivered_record_is_true_and_uses_answers_file() -> None:
    sender, dispatcher = _sender(DeliveryState.DELIVERED)

    notified = sender.notify(_config(Path("repo")), _entry(), ANSWERS_EVENT)

    assert notified is True
    assert dispatcher.calls == [("layout", ANSWERS_EVENT, ANSWERS_PATH)]


def test_notify_answers_on_fresh_started_record_is_true() -> None:
    sender, dispatcher = _sender(DeliveryState.FRESH_STARTED)

    assert sender.notify(_config(Path("repo")), _entry(), ANSWERS_EVENT) is True
    assert dispatcher.calls == [("layout", ANSWERS_EVENT, ANSWERS_PATH)]


def test_notify_answers_on_failed_record_is_false() -> None:
    sender, dispatcher = _sender(DeliveryState.FAILED)

    assert sender.notify(_config(Path("repo")), _entry(), ANSWERS_EVENT) is False
    assert dispatcher.calls == [("layout", ANSWERS_EVENT, ANSWERS_PATH)]


def test_notify_answers_on_unknown_owner_record_is_false() -> None:
    sender, dispatcher = _sender(DeliveryState.UNKNOWN_OWNER)

    assert sender.notify(_config(Path("repo")), _entry(), ANSWERS_EVENT) is False
    assert dispatcher.calls == [("layout", ANSWERS_EVENT, ANSWERS_PATH)]


def test_notify_closed_uses_done_folder(tmp_path: Path) -> None:
    sender, dispatcher = _sender(DeliveryState.DELIVERED)
    cfg = _config(tmp_path)
    done = str(cfg.boards / "done" / "layout" / "answers.json")

    notified = sender.notify(cfg, _entry(), CLOSED_EVENT)

    assert notified is True
    assert dispatcher.calls == [("layout", CLOSED_EVENT, done)]


def test_notify_reopened_uses_rework_brief_when_present(tmp_path: Path) -> None:
    sender, dispatcher = _sender(DeliveryState.DELIVERED)
    cfg = _config(tmp_path)
    cfg.briefs.mkdir(parents=True)
    rework = cfg.briefs / "rework-layout.md"
    rework.write_text("rework the layout", encoding="utf-8")

    notified = sender.notify(cfg, _entry(), REOPENED_EVENT)

    assert notified is True
    assert dispatcher.calls == [("layout", REOPENED_EVENT, str(rework))]


def test_notify_reopened_falls_back_to_answers_file_without_brief(tmp_path: Path) -> None:
    sender, dispatcher = _sender(DeliveryState.DELIVERED)
    cfg = _config(tmp_path)
    cfg.briefs.mkdir(parents=True)

    notified = sender.notify(cfg, _entry(), REOPENED_EVENT)

    assert notified is True
    assert dispatcher.calls == [("layout", REOPENED_EVENT, ANSWERS_PATH)]


def test_notify_note_uses_note_event_and_note_path(tmp_path: Path) -> None:
    sender, dispatcher = _sender(DeliveryState.DELIVERED)

    notified = sender.notify_note(_config(tmp_path), _entry(), _note())

    assert notified is True
    assert dispatcher.calls == [("layout", "note", str(NOTE_PATH))]


def test_notify_builds_dispatcher_for_the_mod() -> None:
    dispatcher = FakeDispatcher(DeliveryState.DELIVERED)
    factory = FakeFactory(dispatcher)
    cfg = _config(Path("repo"))

    BoardNoticeSender(factory).notify(cfg, _entry(), ANSWERS_EVENT)

    assert factory.built == ["CityMod"]
