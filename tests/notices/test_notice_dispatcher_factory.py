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


def _factory(tmp_path: Path, sender: FakePaneSender) -> NoticeDispatcherFactory:
    return NoticeDispatcherFactory(
        pane_directory=FakePaneDirectory(_entry(tmp_path, 'activity = "busy"\n')),
        pane_sender=sender, chat_sink=None,
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


def test_no_owner_resolves_to_fallback_orchestrator(tmp_path: Path) -> None:
    sender = FakePaneSender()
    dispatcher = _factory(tmp_path, sender).build(_config(tmp_path))

    record = dispatcher.dispatch(_board(tmp_path), "question",
                                 "boards/open/b1/board.md")

    assert record.owner == OwnerId(OwnerKind.PANE, ORCHESTRATOR_NAME)
    assert record.state is DeliveryState.UNKNOWN_OWNER
    assert len(sender.lines) == 1
    assert sender.lines[0].startswith("[workbench board] board=")


def test_idle_pane_with_high_context_gets_handoff_prompt(tmp_path: Path) -> None:
    sender = FakePaneSender()
    factory = NoticeDispatcherFactory(
        pane_directory=FakePaneDirectory(
            _entry(tmp_path, 'activity = "idle"\ncontext_percent = 50.0\n')),
        pane_sender=sender, chat_sink=None,
        thread_registry=ThreadRegistry(tmp_path / "threads.json"),
        backends=FakeBackends(), now=lambda: "t", new_id=lambda: "n1")
    notes = tmp_path / "notes"
    notes.mkdir()
    (notes / "handoff-1.md").write_text("the handoff", encoding="utf-8")
    board = _board(tmp_path)
    (board.folder / "owner.json").write_text(
        '{"owner": "pane:main-orchestrator"}', encoding="utf-8")

    record = factory.build(_config(tmp_path)).dispatch(board, "question",
                                                       "boards/open/b1/board.md")

    assert record.state is DeliveryState.FRESH_STARTED
    assert sender.lines[0] == "/clear"
    assert sender.lines[1].startswith("Fresh session started by the workbench.")
    assert "the handoff" in sender.lines[1]
    assert "[workbench board] board=b1 event=question. Read boards/open/b1/board.md." \
        in sender.lines[1]
