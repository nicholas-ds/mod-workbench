"""Assemble a NoticeDispatcher for one mod from real parts."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from workbench.chat.chat_backend_resolver import ChatBackendResolver
from workbench.chat.thread_registry import ChatThread, ThreadRegistry
from workbench.core.config import ModConfig
from workbench.mods.pane_directory import PaneDirectory
from workbench.notices.board_owner_store import BoardOwnerStore
from workbench.notices.chat_recipient import ChatRecipient
from workbench.notices.context_policy import ContextPolicy
from workbench.notices.fresh_start_prompt import FreshStartPrompt
from workbench.notices.notice_composer import NoticeComposer
from workbench.notices.notice_dispatcher import NoticeDispatcher
from workbench.notices.owner_id import OwnerKind, OwnerId
from workbench.notices.owner_inbox import OwnerInbox
from workbench.notices.owner_resolver import OwnerResolver
from workbench.notices.pane_activity_reader import PaneActivityReader
from workbench.notices.pane_context_reader import PaneContextReader
from workbench.notices.pane_recipient import PaneRecipient
from workbench.notices.repo_session_recipient import RepoSessionRecipient
from workbench.notices.recipient_resolver import RecipientResolver
from workbench.panes.chat_turn_sink import ChatTurnSink
from workbench.panes.pane_registry import OrchestratorPane
from workbench.panes.pane_sender import PaneSender


class LatestHandoffReader:
    """Read the newest handoff file of a repo's notes folder."""

    def __init__(self, notes_dir: Path) -> None:
        self._notes_dir = notes_dir

    def read(self, owner: OwnerId) -> str | None:
        """Return the text of the newest `handoff-*.md`, None when there is none."""
        paths = sorted(self._notes_dir.glob("handoff-*.md"),
                       key=lambda path: path.stat().st_mtime)
        if not paths:
            return None
        try:
            return paths[-1].read_text(encoding="utf-8")
        except OSError:
            return None


class NoticeDispatcherFactory:
    """Wire the delivery pipeline for one mod from injected parts."""

    def __init__(self, pane_directory: PaneDirectory, pane_sender: PaneSender,
                 chat_sink: ChatTurnSink | None, thread_registry: ThreadRegistry,
                 backends: ChatBackendResolver, now: Callable[[], str],
                 new_id: Callable[[], str]) -> None:
        self._pane_directory = pane_directory
        self._pane_sender = pane_sender
        self._chat_sink = chat_sink
        self._thread_registry = thread_registry
        self._backends = backends
        self._now = now
        self._new_id = new_id

    def build(self, cfg: ModConfig) -> NoticeDispatcher:
        """Build the dispatcher: recipients, resolver, inbox and handoff reader."""
        def find_pane(owner: OwnerId) -> OrchestratorPane | None:
            entry = self._pane_directory.find(owner.key)
            return None if entry is None else entry.pane

        def status_file_of(owner: OwnerId) -> Path | None:
            entry = self._pane_directory.find(owner.key)
            return None if entry is None else entry.status_file

        pane_recipient = PaneRecipient(
            find_pane, self._pane_sender, PaneContextReader(status_file_of),
            PaneActivityReader(status_file_of).is_idle)
        chat_recipient = ChatRecipient(
            self._send_turn(),
            lambda name: self._backends.backend_of(name).context_percent(name),
            self._is_known,
            lambda name: ChatThread.split_name(name)[0],
            lambda orchestrator: self._thread_registry.add(orchestrator).name)
        repo_recipient = RepoSessionRecipient(
            self._send_turn(),
            lambda orchestrator: self._thread_registry.add(orchestrator).name)
        recipients = RecipientResolver({OwnerKind.PANE: pane_recipient,
                                        OwnerKind.CHAT: chat_recipient,
                                        OwnerKind.REPO: repo_recipient})
        return NoticeDispatcher(
            owner_resolver=OwnerResolver(
                BoardOwnerStore(), OwnerId(OwnerKind.REPO, cfg.name),
                lambda owner: recipients.resolve(owner).is_reachable(owner)),
            composer=NoticeComposer(), inbox=OwnerInbox.of_mod(cfg.repo),
            recipient_resolver=recipients,
            context_policy=ContextPolicy(), fresh_prompt=FreshStartPrompt(),
            handoff_text_of=LatestHandoffReader(cfg.repo / "notes").read,
            new_id=self._new_id, now=self._now)

    def _send_turn(self) -> Callable[[str, str], bool]:
        if self._chat_sink is None:
            return lambda name, text: False
        return self._chat_sink.send

    def _is_known(self, name: str) -> bool:
        return (ChatThread.split_name(name)[1] == ""
                or self._thread_registry.contains(name))
