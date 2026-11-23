"""Stop hook: save the last chat message as the author reply, and block an idle stop."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

GLOB_PATTERNS = ("*/status/*.toml", "*/status/workspaces/*.toml")
READ_LIMIT_BYTES = 64 * 1024
FINISHED_LINE = re.compile(r'^\s*phase\s*=\s*"finished"')
PERMANENT_TAG = "permanent"  # mirrors workbench/boards/permanent_board.py; scripts/ cannot import workbench
BLOCK_REASON = (
    "You have no open board and no finished status. Permanent boards do not count. "
    "Raise a board for the next author decision with the workbench-board skill. "
    'Or set phase = "finished" and summary = "<one line>" in your status file. '
    "Do not stop with open tasks."
)


@dataclass(frozen=True)
class Workspace:
    """One registered orchestrator: its repo and status file."""

    repo: Path
    status_file: Path


class WorkspaceLocator:
    """Find the workspace that owns one wmux surface."""

    def locate(self, root: Path, surface_id: str) -> Workspace | None:
        for pattern in GLOB_PATTERNS:
            for path in sorted(root.glob(pattern)):
                if self._owns(path, surface_id):
                    return Workspace(self._repo_of(path), path)
        return None

    def _owns(self, path: Path, surface_id: str) -> bool:
        try:
            return f'wmux_surface = "{surface_id}"' in path.read_text(encoding="utf-8")
        except OSError:
            return False

    def _repo_of(self, path: Path) -> Path:
        return path.parents[2] if path.parent.name == "workspaces" else path.parents[1]


class TranscriptReader:
    """Read the last assistant text of a Claude Code transcript."""

    def last_assistant_text(self, transcript: Path) -> str:
        lines = self._tail_lines(transcript)
        for line in reversed(lines):
            text = self._assistant_text(line)
            if text:
                return text
        return ""

    def _tail_lines(self, transcript: Path) -> list[str]:
        try:
            with transcript.open("rb") as handle:
                handle.seek(0, os.SEEK_END)
                size = handle.tell()
                handle.seek(max(0, size - READ_LIMIT_BYTES))
                tail = handle.read()
        except OSError:
            return []
        return tail.decode("utf-8", errors="replace").splitlines()

    def _assistant_text(self, line: str) -> str:
        try:
            entry = json.loads(line)
        except ValueError:
            return ""
        if entry.get("type") != "assistant":
            return ""
        content = entry.get("message", {}).get("content", [])
        if not isinstance(content, list):
            return ""
        parts = [block.get("text", "") for block in content if block.get("type") == "text"]
        return "\n".join(part for part in parts if part).strip()


class ReplyCapturer:
    """Answer each unhandled author message with the agent's last chat text."""

    def capture(self, repo: Path, reply_text: str) -> int:
        messages = repo / "messages"
        pending = sorted(messages.glob("*.md")) if messages.is_dir() else []
        for message in pending:
            self._answer(messages, message, reply_text)
        if not pending and reply_text:
            self._record_unprompted(messages, reply_text, datetime.now(timezone.utc))
        return len(pending)

    def _record_unprompted(self, messages: Path, reply_text: str, now: datetime) -> None:
        """Keep a chat reply that no author message asked for, so the UI thread shows it."""
        replies = messages / "replies"
        if self._is_latest_reply(replies, reply_text):
            return
        message_id = now.strftime("%Y%m%dT%H%M%S+0000") + "-agent"
        done = messages / "done"
        done.mkdir(parents=True, exist_ok=True)
        replies.mkdir(exist_ok=True)
        created = now.isoformat(timespec="seconds")
        (done / f"{message_id}.md").write_text(
            f"---\ncreated: '{created}'\nview: agent\n---\nAgent update. No author message was waiting.\n",
            encoding="utf-8")
        (replies / f"{message_id}.md").write_text(reply_text + "\n", encoding="utf-8")

    def _is_latest_reply(self, replies: Path, reply_text: str) -> bool:
        files = sorted(replies.glob("*.md"), key=lambda path: path.stat().st_mtime) if replies.is_dir() else []
        return bool(files) and files[-1].read_text(encoding="utf-8").strip() == reply_text.strip()

    def _answer(self, messages: Path, message: Path, reply_text: str) -> None:
        reply = messages / "replies" / f"{message.stem}.md"
        if not reply.exists() and reply_text:
            reply.parent.mkdir(exist_ok=True)
            reply.write_text(reply_text + "\n", encoding="utf-8")
        done = messages / "done"
        done.mkdir(exist_ok=True)
        try:
            message.replace(done / message.name)
        except OSError:
            return


class StopGate:
    """Decide whether an orchestrator may stop."""

    def may_stop(self, workspace: Workspace) -> bool:
        return self._has_open_board(workspace.repo) or self._is_finished(workspace.status_file)

    def _has_open_board(self, repo: Path) -> bool:
        boards = repo / "boards" / "open"
        if not boards.is_dir():
            return False
        return any(not self._is_permanent(path) for path in boards.iterdir() if path.is_dir())

    def _is_permanent(self, board: Path) -> bool:
        """True when board.md front matter carries the permanent tag; read as plain text."""
        try:
            lines = (board / "board.md").read_text(encoding="utf-8").splitlines()
        except OSError:
            return False
        return any(line.startswith("tags:") and PERMANENT_TAG in line for line in lines)

    def _is_finished(self, status_file: Path) -> bool:
        try:
            lines = status_file.read_text(encoding="utf-8").splitlines()
        except OSError:
            return False
        return any(FINISHED_LINE.match(line) for line in lines)


def handle_stop(payload: dict, surface_id: str, root: Path) -> str | None:
    """Save the reply, then return the block message when the agent may not stop."""
    workspace = WorkspaceLocator().locate(root, surface_id)
    if workspace is None:
        return None
    reply_text = payload.get("last_assistant_message") or TranscriptReader().last_assistant_text(
        Path(payload.get("transcript_path", "")))
    ReplyCapturer().capture(workspace.repo, reply_text)
    if payload.get("stop_hook_active") or StopGate().may_stop(workspace):
        return None
    return json.dumps({"decision": "block", "reason": BLOCK_REASON})
