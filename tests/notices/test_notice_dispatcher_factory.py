"""Tests for NoticeDispatcherFactory: built dispatcher and the fallback owner."""

from pathlib import Path

from workbench.chat.thread_registry import ThreadRegistry
from workbench.core.config import ModConfig
from workbench.boards.board_types import Board
from workbench.mods.pane_directory import ORCHESTRATOR_NAME, PaneEntry
from workbench.notices.notice_dispatcher import NoticeDispatcher
from workbench.notices.notice_dispatcher_factory import NoticeDispatcherFactory
from workbench.notices.notice_types import DeliveryState
from workbench.notices.owner_id import OwnerId, OwnerKind
from workbench.panes.pane_registry import OrchestratorPane


class FakePaneDirectory:
    """Answer find() with one fixed entry for the orchestrator name."""

    def __init__(self, entry: PaneEntry | None) -> None:
        self._entry = entry

    def find(self, name: str) -> PaneEntry | None:
        return self._entry if name == ORCHESTRATOR_NAME else None


class FakePaneSender:
    """Record every line handed to a pane."""

    def __init__(self) -> None:
        self.lines: list[str] = []

    def send(self, pane: OrchestratorPane, text: str) -> bool:
        self.lines.append(text)
        return True


class FakeChatSink:
    """Record every chat turn as (thread name, text)."""

    def __init__(self) -> None:
        self.turns: list[tuple[str, str]] = []

    def send(self, name: str, text: str) -> bool:
        self.turns.append((name, text))
        return True


class FakeBackend:
    """A backend that cannot measure context."""

    def context_percent(self, name: str) -> float | None:
        return None


class FakeBackends:
    """Resolve every chat name to one backend."""

    def backend_of(self, name: str) -> FakeBackend:
        return FakeBackend()


def _entry(tmp_path: Path, toml: str) -> PaneEntry:
    status_file = tmp_path / "status" / "main-orchestrator.toml"
    status_file.parent.mkdir(parents=True, exist_ok=True)
    status_file.write_text(toml, encoding="utf-8")
    return PaneEntry(name=ORCHESTRATOR_NAME, mod=None, repo=tmp_path,
                     pane=OrchestratorPane(surface="s1"), status_file=status_file)


def _config(tmp_path: Path) -> ModConfig:
    return ModConfig(name="demo", repo=tmp_path, platform=tmp_path, screens=(),
                     boards=tmp_path / "boards", status=tmp_path / "status",
                     tracking=tmp_path, log=tmp_path, briefs=tmp_path,
                     exports=tmp_path)


def _factory(tmp_path: Path, sender: FakePaneSender,
             chat_sink: FakeChatSink | None = None) -> NoticeDispatcherFactory:
    return NoticeDispatcherFactory(
        pane_directory=FakePaneDirectory(_entry(tmp_path, 'activity = "busy"\n')),
        pane_sender=sender, chat_sink=chat_sink,
        thread_registry=ThreadRegistry(tmp_path / "threads.json"),
        backends=FakeBackends(), now=lambda: "2026-11-23T10:00:00",
        new_id=lambda: "n1")


def _board(tmp_path: Path) -> Board:
    folder = tmp_path / "boards" / "open" / "b1"
    folder.mkdir(parents=True, exist_ok=True)
    return Board(id="b1", folder=folder, title="t")


def test_build_returns_dispatcher(tmp_path: Path) -> None:
    factory = _factory(tmp_path, FakePaneSender())

    dispatcher = factory.build(_config(tmp_path))

    assert isinstance(dispatcher, NoticeDispatcher)


def test_no_owner_starts_a_new_session_in_the_repo(tmp_path: Path) -> None:
    chat_sink = FakeChatSink()
    sender = FakePaneSender()
    dispatcher = _factory(tmp_path, sender, chat_sink).build(_config(tmp_path))

    record = dispatcher.dispatch(_board(tmp_path), "question",
                                 "boards/open/b1/board.md")

    assert record.owner == OwnerId(OwnerKind.REPO, "demo")
    assert record.state is DeliveryState.UNKNOWN_OWNER
    assert sender.lines == []
    assert [name for name, _ in chat_sink.turns] == ["demo~t1"]
    assert chat_sink.turns[0][1].startswith("[workbench] board=")
