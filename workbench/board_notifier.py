"""Tell the workspace pane that its board has news."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from workbench.board_types import Board, BoardEntry
from workbench.chat_turn_sink import ChatTurnSink
from workbench.config import ModConfig
from workbench.message_writer import MessageContext, MessageWriter
from workbench.pane_registry import OrchestratorPane, PaneRegistry
from workbench.pane_sender import PaneMessageFormatter, PaneSender

ANSWERS_EVENT = "answers"
CLOSED_EVENT = "closed"
REOPENED_EVENT = "reopened"

ANSWERS_FILE = "answers.json"

CHAT_PREFIX = "chat-"


def utc_now() -> str:
    """Return the current UTC time as seconds-precision ISO text."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class NoteNotice:
    """One pinned note to announce to the pane that raised the board."""

    item: str
    x: float
    y: float
    text: str
    path: Path


class BoardNotifier:
    """Tell the agent that raised a board about a board event:
    an app chat gets a turn, a terminal gets a pane line."""

    def __init__(self, sender: PaneSender,
                 writer: MessageWriter = MessageWriter(),
                 formatter: PaneMessageFormatter = PaneMessageFormatter(),
                 now: Callable[[], str] = utc_now,
                 chat_sink: ChatTurnSink | None = None) -> None:
        self._sender = sender
        self._writer = writer
        self._formatter = formatter
        self._now = now
        self._chat_sink = chat_sink

    def notify(self, cfg: ModConfig, entry: BoardEntry, event: str) -> bool:
        return self._route(cfg, entry, self._event_text(entry, event))

    def notify_note(self, cfg: ModConfig, entry: BoardEntry, notice: NoteNotice) -> bool:
        return self._route(cfg, entry, self._note_text(notice))

    def _route(self, cfg: ModConfig, entry: BoardEntry, event_text: str) -> bool:
        chat_name = self._chat_name(entry.board)
        if chat_name:
            return self._send_to_chat(cfg, entry, chat_name, event_text)
        pane = self._pane(cfg, entry.board)
        if pane is None:
            return False
        return self._deliver(cfg, entry, pane, event_text)

    def _send_to_chat(self, cfg: ModConfig, entry: BoardEntry, chat_name: str,
                      event_text: str) -> bool:
        if self._chat_sink is None:
            return False
        text = (f"[workbench board] mod={cfg.name} board={entry.board.id}. "
                f"{event_text}")
        return self._chat_sink.send(chat_name, text)

    def _chat_name(self, board: Board) -> str:
        if isinstance(board.raised_by, str) and board.raised_by.startswith(CHAT_PREFIX):
            return board.raised_by[len(CHAT_PREFIX):]
        return ""

    def _deliver(self, cfg: ModConfig, entry: BoardEntry, pane: OrchestratorPane,
                 event_text: str) -> bool:
        now = self._now()
        context = MessageContext(view="board", board=entry.board.id)
        message_id = self._writer.write(cfg.repo, event_text, context, now)
        reply_file = cfg.repo / "messages" / "replies" / f"{message_id}.md"
        line = self._formatter.format(cfg.name, context, event_text, message_id, reply_file)
        return self._sender.send(pane, line)

    def _pane(self, cfg: ModConfig, board: Board) -> OrchestratorPane | None:
        pane_file = cfg.status / f"{board.raised_by}.toml"
        return PaneRegistry(pane_file).find()

    @staticmethod
    def _event_text(entry: BoardEntry, event: str) -> str:
        return (f"event={event} answered={BoardNotifier._answered(entry)}. "
                f"{BoardNotifier._instruction(entry.board, event)}")

    @staticmethod
    def _note_text(notice: NoteNotice) -> str:
        at = f"{round(notice.x * 100)}%,{round(notice.y * 100)}%"
        return (f"event=note item={notice.item} at={at}. {notice.text}. "
                f"Note file: {notice.path}")

    @staticmethod
    def _answered(entry: BoardEntry) -> str:
        return f"{len(entry.answers)}/{len(entry.board.questions)}"

    @staticmethod
    def _instruction(board: Board, event: str) -> str:
        if event == ANSWERS_EVENT:
            return (f"The author sent answers. Read {board.folder / ANSWERS_FILE} "
                    f"and act on it. Unanswered questions use their defaults.")
        if event == REOPENED_EVENT:
            return "The author reopened this board. Read the rework brief and act on it."
        done = board.folder.parent.parent / "done" / board.id / ANSWERS_FILE
        return f"The author closed this board. Read {done} and act on it."
