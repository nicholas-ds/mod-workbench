"""Author message route of one mod: save a message file for the agents."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
import tomllib

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from workbench.mods.message_reader import MessageReader
from workbench.panes.message_writer import MessageContext, MessageWriter
from workbench.mods.mod_registry import ModRegistry
from workbench.mods.pane_directory import ORCHESTRATOR_NAME, PaneDirectory, PaneEntry
from workbench.panes.pane_registry import OrchestratorPane, PaneRegistry
from workbench.panes.pane_sender import PaneMessageFormatter, PaneSender


class MessageContextPost(BaseModel):
    """Context of one author message post."""

    model_config = ConfigDict(frozen=True)

    view: str
    board: str | None = None
    item: str | None = None
    question: str | None = None


class MessagePost(BaseModel):
    """Body of one author message post."""

    model_config = ConfigDict(frozen=True)

    text: str
    target: str | None = None
    context: MessageContextPost


class MessagesRoutes:
    """Author message route of one mod: save a message file for the agents."""

    def __init__(self, registry: ModRegistry, writer: MessageWriter,
                 reader: MessageReader | None = None,
                 pane_registry: PaneRegistry | None = None,
                 pane_sender: PaneSender | None = None,
                 workbench_root: Path | None = None, *,
                 pane_directory: PaneDirectory | None = None) -> None:
        self._registry, self._writer = registry, writer
        self._workbench_root = workbench_root
        self._reader = reader if reader is not None else MessageReader()
        self._pane_registry, self._pane_sender = pane_registry, pane_sender
        self._pane_directory = pane_directory
        self._formatter = PaneMessageFormatter()
        self.routes = APIRouter()
        self.routes.add_api_route("/api/mods/{name}/messages", self.messages,
                                  methods=["GET"])
        self.routes.add_api_route("/api/messages", self.workbench_message,
                                  methods=["POST"])
        self.routes.add_api_route("/api/messages", self.workbench_messages,
                                  methods=["GET"])
        self.routes.add_api_route("/api/panes", self.panes, methods=["GET"])

    def messages(self, name: str) -> dict[str, object]:
        return self._list(self._registry.require(name).repo)

    def workbench_messages(self) -> dict[str, object]:
        return self._list(self._require_root())

    def workbench_message(self, body: MessagePost) -> dict[str, object]:
        if body.target in (None, ORCHESTRATOR_NAME):
            return self._post("workbench", self._require_root(), body)
        entry = self._require_directory().find(body.target)
        if entry is None:
            raise HTTPException(status_code=404,
                                detail=f"unknown pane: {body.target}")
        return self._post(self._sender_name(entry), entry.repo, body, entry.pane)

    def panes(self) -> dict[str, object]:
        return {"panes": [{"name": entry.name, "mod": entry.mod,
                           "active_at": self._activity_at(entry.status_file)}
                          for entry in self._require_directory().list_all()]}

    @staticmethod
    def _activity_at(status_file: Path) -> str:
        try:
            data = tomllib.loads(status_file.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
            return ""
        activity = data.get("activity_at")
        return activity if isinstance(activity, str) else ""

    def _require_root(self) -> Path:
        if self._workbench_root is None:
            raise HTTPException(status_code=404, detail="no workbench folder")
        return self._workbench_root

    def _require_directory(self) -> PaneDirectory:
        if self._pane_directory is None:
            raise HTTPException(status_code=404, detail="no pane directory")
        return self._pane_directory

    def _list(self, repo: Path) -> dict[str, object]:
        return {"messages": [asdict(record) for record in self._reader.read_all(repo)]}

    def _post(self, name: str, repo: Path, body: MessagePost,
              pane: OrchestratorPane | None = None) -> dict[str, object]:
        now = datetime.now(UTC).isoformat(timespec="seconds")
        try:
            message_id = self._writer.write(repo, body.text, self._context(body.context),
                                            now)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        reply_file = repo / "messages" / "replies" / f"{message_id}.md"
        delivered = self._deliver(name, body, pane, message_id, reply_file)
        return {"id": message_id, "delivered": delivered}

    def _deliver(self, name: str, body: MessagePost, pane: OrchestratorPane | None,
                 message_id: str, reply_file: Path) -> bool:
        if self._pane_sender is None:
            return False
        target = pane if pane is not None else self._default_pane()
        if target is None:
            return False
        line = self._formatter.format(name, self._context(body.context), body.text,
                                      message_id, reply_file)
        return self._pane_sender.send(target, line)

    def _default_pane(self) -> OrchestratorPane | None:
        if self._pane_registry is None:
            return None
        return self._pane_registry.find()

    @staticmethod
    def _sender_name(entry: PaneEntry) -> str:
        return entry.mod if entry.mod is not None else "workbench"

    @staticmethod
    def _context(context: MessageContextPost) -> MessageContext:
        return MessageContext(view=context.view, board=context.board, item=context.item,
                              question=context.question)
