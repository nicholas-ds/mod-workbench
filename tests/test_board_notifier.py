"""Tests: BoardNotifier writes a message file, then types its line into the pane."""

from pathlib import Path

from api_fixtures import MOD_TOML
from workbench.board_notifier import (ANSWERS_EVENT, CLOSED_EVENT, REOPENED_EVENT,
                                      BoardNotifier, NoteNotice)
from workbench.board_types import Answer, Board, BoardEntry, Question
from workbench.config import ModConfig, ModConfigLoader
from workbench.message_writer import MessageWriter
from workbench.pane_registry import OrchestratorPane
from workbench.pane_sender import PaneMessageFormatter

NOW = "2026-11-09T12:00:00"
MESSAGE_ID = "20261109T120000-1"
ANSWERS_PATH = Path("boards/open/layout") / "answers.json"
DONE_PATH = Path("boards/done/layout") / "answers.json"
NOTE_PATH = Path("notes/layout-1.md")


class RecordingSender:
    """Fake PaneSender that records the lines it is asked to type."""

    def __init__(self) -> None:
        self.lines: list[str] = []

    def send(self, pane: OrchestratorPane, text: str) -> bool:
        self.lines.append(text)
        return True


class RecordingChatSink:
    """Fake ChatTurnSink that records the turns it is asked to send."""

    def __init__(self) -> None:
        self.turns: list[tuple[str, str]] = []

    def send(self, name: str, text: str) -> bool:
        self.turns.append((name, text))
        return True


def make_cfg(root: Path) -> ModConfig:
    repo = root / "CityMod"
    (repo / "status").mkdir(parents=True)
    (repo / "workbench.toml").write_text(MOD_TOML.replace('status = "status.toml"',
                                                          'status = "status"'),
                                         encoding="utf-8")
    return ModConfigLoader().load(repo)


def make_board(raised_by: str = "build") -> Board:
    question = Question(id="layout", type="choice", prompt="Which queue layout?")
    return Board(id="layout", folder=Path("boards/open/layout"),
                 title="Queue layout", raised_by=raised_by, questions=(question,))


def make_entry(answers: tuple[Answer, ...] = (),
               raised_by: str = "build") -> BoardEntry:
    return BoardEntry(board=make_board(raised_by), answers=answers)


def write_pane_file(cfg: ModConfig) -> None:
    (cfg.status / "build.toml").write_text('wmux_surface = "surf-1"', encoding="utf-8")


def make_notifier(sender: RecordingSender) -> BoardNotifier:
    return BoardNotifier(sender, MessageWriter(), PaneMessageFormatter(), lambda: NOW)


def make_chat_notifier(sender: RecordingSender,
                       sink: RecordingChatSink | None) -> BoardNotifier:
    return BoardNotifier(sender, MessageWriter(), PaneMessageFormatter(), lambda: NOW,
                         chat_sink=sink)


def expected_line(cfg: ModConfig, event_text: str) -> str:
    reply_file = cfg.repo / "messages" / "replies" / f"{MESSAGE_ID}.md"
    return (f"[workbench] mod={cfg.name} view=board board=layout id={MESSAGE_ID} | "
            f"{event_text} | Reply in the workbench UI: write your answer to {reply_file} "
            f"(plain text), then move the message file to messages/done/. "
            f"Do not answer only in chat.")


def message_file(cfg: ModConfig) -> Path:
    return cfg.repo / "messages" / f"{MESSAGE_ID}.md"


def test_notify_types_answers_line_and_writes_message_file(tmp_path: Path) -> None:
    cfg = make_cfg(tmp_path)
    write_pane_file(cfg)
    sender = RecordingSender()
    answer = Answer(question_id="layout", picked="wide")
    event_text = (f"event=answers answered=1/1. The author sent answers. "
                  f"Read {ANSWERS_PATH} and act on it. "
                  f"Unanswered questions use their defaults.")
    notified = make_notifier(sender).notify(cfg, make_entry((answer,)), ANSWERS_EVENT)
    assert notified is True
    assert sender.lines == [expected_line(cfg, event_text)]
    text = message_file(cfg).read_text(encoding="utf-8")
    assert "view: board" in text
    assert "board: layout" in text
    assert event_text in text


def test_notify_types_closed_line_and_writes_message_file(tmp_path: Path) -> None:
    cfg = make_cfg(tmp_path)
    write_pane_file(cfg)
    sender = RecordingSender()
    event_text = (f"event=closed answered=0/1. The author closed this board. "
                  f"Read {DONE_PATH} and act on it.")
    notified = make_notifier(sender).notify(cfg, make_entry(), CLOSED_EVENT)
    assert notified is True
    assert sender.lines == [expected_line(cfg, event_text)]
    assert message_file(cfg).is_file()


def test_notify_types_reopened_line_and_writes_message_file(tmp_path: Path) -> None:
    cfg = make_cfg(tmp_path)
    write_pane_file(cfg)
    sender = RecordingSender()
    event_text = ("event=reopened answered=0/1. The author reopened this board. "
                  "Read the rework brief and act on it.")
    notified = make_notifier(sender).notify(cfg, make_entry(), REOPENED_EVENT)
    assert notified is True
    assert sender.lines == [expected_line(cfg, event_text)]
    assert message_file(cfg).is_file()


def test_notify_without_pane_file_is_false(tmp_path: Path) -> None:
    cfg = make_cfg(tmp_path)
    sender = RecordingSender()
    notified = make_notifier(sender).notify(cfg, make_entry(), CLOSED_EVENT)
    assert notified is False
    assert sender.lines == []
    assert not (cfg.repo / "messages").exists()


def test_notify_note_types_exact_line_and_writes_message_file(tmp_path: Path) -> None:
    cfg = make_cfg(tmp_path)
    write_pane_file(cfg)
    sender = RecordingSender()
    notice = NoteNotice(item="shot.png", x=0.5, y=0.25, text="look here",
                        path=NOTE_PATH)
    event_text = f"event=note item=shot.png at=50%,25%. look here. Note file: {NOTE_PATH}"
    notified = make_notifier(sender).notify_note(cfg, make_entry(), notice)
    assert notified is True
    assert sender.lines == [expected_line(cfg, event_text)]
    assert event_text in message_file(cfg).read_text(encoding="utf-8")


def test_notify_note_without_pane_file_is_false(tmp_path: Path) -> None:
    cfg = make_cfg(tmp_path)
    sender = RecordingSender()
    notice = NoteNotice(item="shot.png", x=0.5, y=0.25, text="look here",
                        path=NOTE_PATH)
    notified = make_notifier(sender).notify_note(cfg, make_entry(), notice)
    assert notified is False
    assert sender.lines == []
    assert not (cfg.repo / "messages").exists()


def test_notify_on_chat_board_sends_turn_without_message_file(tmp_path: Path) -> None:
    cfg = make_cfg(tmp_path)
    sender = RecordingSender()
    sink = RecordingChatSink()
    notified = make_chat_notifier(sender, sink).notify(cfg, make_entry(raised_by="chat-main"),
                                                       CLOSED_EVENT)
    assert notified is True
    assert len(sink.turns) == 1
    name, text = sink.turns[0]
    assert name == "main"
    assert text.startswith("[workbench board] mod=")
    assert "board=layout" in text
    assert "event=closed" in text
    assert sender.lines == []
    assert not (cfg.repo / "messages" / f"{MESSAGE_ID}.md").exists()
    assert not (cfg.repo / "messages").exists()


def test_notify_note_on_chat_board_sends_turn(tmp_path: Path) -> None:
    cfg = make_cfg(tmp_path)
    sender = RecordingSender()
    sink = RecordingChatSink()
    notice = NoteNotice(item="shot.png", x=0.5, y=0.25, text="look here",
                        path=NOTE_PATH)
    notified = make_chat_notifier(sender, sink).notify_note(cfg, make_entry(raised_by="chat-main"),
                                                            notice)
    assert notified is True
    assert len(sink.turns) == 1
    name, text = sink.turns[0]
    assert name == "main"
    assert "event=note" in text
    assert "board=layout" in text
    assert sender.lines == []
    assert not (cfg.repo / "messages").exists()


def test_notify_on_chat_board_without_sink_is_false(tmp_path: Path) -> None:
    cfg = make_cfg(tmp_path)
    sender = RecordingSender()
    notified = make_chat_notifier(sender, None).notify(cfg, make_entry(raised_by="chat-main"),
                                                       CLOSED_EVENT)
    assert notified is False
    assert sender.lines == []
    assert not (cfg.repo / "messages").exists()
