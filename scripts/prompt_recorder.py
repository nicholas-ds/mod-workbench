"""UserPromptSubmit hook: save each prompt typed in the CLI as a message file, so the UI shows the whole thread."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from stop_gate import WorkspaceLocator

SKIPPED_PREFIXES = ("[workbench]", "<task-notification", "<system-reminder", "<local-command")


class CliPromptRecorder:
    """Write one CLI prompt into the messages folder of a repo."""

    def record(self, repo: Path, prompt: str, now: datetime) -> Path | None:
        text = prompt.strip()
        if not text or text.startswith(SKIPPED_PREFIXES):
            return None
        messages = repo / "messages"
        messages.mkdir(exist_ok=True)
        path = self._free_path(messages, now)
        path.write_text(self._file_text(text, now), encoding="utf-8")
        return path

    def _free_path(self, messages: Path, now: datetime) -> Path:
        prefix = now.strftime("%Y%m%dT%H%M%S+0000")
        number = 1
        while True:
            path = messages / f"{prefix}-{number}.md"
            try:
                path.open("x").close()
            except FileExistsError:
                number += 1
                continue
            return path

    def _file_text(self, text: str, now: datetime) -> str:
        created = now.isoformat(timespec="seconds")
        return f"---\ncreated: '{created}'\nview: cli\n---\n{text}\n"


def handle_prompt(payload: dict, surface_id: str, root: Path) -> None:
    workspace = WorkspaceLocator().locate(root, surface_id)
    if workspace is not None:
        CliPromptRecorder().record(workspace.repo, payload.get("prompt", ""),
                                   datetime.now(timezone.utc))
