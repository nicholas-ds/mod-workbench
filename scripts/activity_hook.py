"""Record whether an orchestrator session is working, in its status file."""

from __future__ import annotations

import json
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

from board_owner_stamper import BoardOwnerStamper
from pane_name_finder import PaneNameFinder
from prompt_recorder import handle_prompt
from session_follower import SessionFollower
from stop_gate import handle_stop
from thread_archiver import handle_session_start
from tool_activity import ToolEventClassifier

EVENT_STATES = {"UserPromptSubmit": "working", "Stop": "idle", "SessionEnd": "idle"}
TOOL_EVENTS = ("PreToolUse", "Notification")
IDLE_CLEARED_KEYS = ("task", "last_tool_at", "last_tool", "last_file", "tool_calls")
GLOB_PATTERNS = ("*/status/*.toml", "*/status/workspaces/*.toml")
CHAT_SESSION_ENV = "WORKBENCH_CHAT_SESSION"
ERROR_LOG = Path(__file__).resolve().parents[1] / "status" / "hook-errors.log"


class ActivityRecorder:
    """Write the activity state into every status file of one surface."""

    def update(self, root: Path, surface_id: str, state: str, now: str,
               last_tool: str | None = None, edited_file: str = "",
               prompt_started: bool = False) -> None:
        for path in self._candidate_paths(root):
            try:
                self._update_file(path, surface_id, state, now, last_tool,
                                  edited_file, prompt_started)
            except OSError:
                continue

    def _candidate_paths(self, root: Path) -> list[Path]:
        found = {path for pattern in GLOB_PATTERNS for path in root.glob(pattern)}
        return sorted(found)

    def _update_file(self, path: Path, surface_id: str, state: str, now: str,
                     last_tool: str | None, edited_file: str,
                     prompt_started: bool) -> None:
        with path.open("r", encoding="utf-8", newline="") as handle:
            text = handle.read()
        if f'wmux_surface = "{surface_id}"' not in text:
            return
        lines = self._edit_lines(text.splitlines(), state, now, last_tool,
                                 edited_file, prompt_started)
        self._write_atomically(path, self._join(lines, text))

    def _write_atomically(self, path: Path, text: str) -> None:
        temp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
        with temp.open("w", encoding="utf-8", newline="") as handle:
            handle.write(text)
        os.replace(temp, path)

    def _edit_lines(self, lines: list[str], state: str, now: str,
                    last_tool: str | None, edited_file: str,
                    prompt_started: bool) -> list[str]:
        lines = self._set_line(lines, "activity", f'activity = "{state}"')
        lines = self._set_line(lines, "activity_at", f'activity_at = "{now}"')
        if state == "idle":
            lines = [line for line in lines if not self._is_cleared_on_idle(line)]
        if prompt_started:
            lines = [line for line in lines if not self._is_key_line(line, "phase")]
        if last_tool is not None:
            count = self._int_value(lines, "tool_calls") + 1
            lines = self._set_line(lines, "tool_calls", f"tool_calls = {count}")
            lines = self._set_line(lines, "last_tool", f'last_tool = "{last_tool}"')
            lines = self._set_line(lines, "last_tool_at", f'last_tool_at = "{now}"')
            if edited_file:
                lines = self._set_line(lines, "last_file", f'last_file = "{edited_file}"')
        elif state == "working":
            lines = self._set_line(lines, "tool_calls", "tool_calls = 0")
        return lines

    def _int_value(self, lines: list[str], key: str) -> int:
        for line in lines:
            if self._is_key_line(line, key):
                try:
                    return int(line.split("=", 1)[1].strip())
                except ValueError:
                    return 0
        return 0

    def _is_cleared_on_idle(self, line: str) -> bool:
        return any(self._is_key_line(line, key) for key in IDLE_CLEARED_KEYS)

    def _set_line(self, lines: list[str], key: str, value_line: str) -> list[str]:
        replaced = False
        result: list[str] = []
        for line in lines:
            if self._is_key_line(line, key):
                result.append(value_line)
                replaced = True
            else:
                result.append(line)
        if not replaced:
            result.insert(self._first_table_index(result), value_line)
        return result

    def _first_table_index(self, lines: list[str]) -> int:
        for index, line in enumerate(lines):
            if line.lstrip().startswith("["):
                return index
        return len(lines)

    def _is_key_line(self, line: str, key: str) -> bool:
        return line.startswith(key) and line[len(key) :].lstrip().startswith("=")

    def _join(self, lines: list[str], original_text: str) -> str:
        newline = "\r\n" if "\r\n" in original_text else "\n"
        text = newline.join(lines)
        if original_text.endswith(("\n", "\r")):
            text += newline
        return text


def _follow_clear(payload: dict[str, object], event: str | None,
                  surface_id: str | None) -> None:
    surface_key = surface_id or "terminal"
    status_dir = Path(__file__).resolve().parents[1] / "status"
    if event == "SessionEnd" and payload.get("reason") == "clear":
        SessionFollower(status_dir).remember_cleared(
            surface_key, payload.get("session_id", ""))
    if event == "SessionStart" and payload.get("source") == "clear":
        SessionFollower(status_dir).follow_new(
            surface_key, payload.get("session_id", ""))


def main() -> int:
    """One entry point for every session: it is the hook all sessions already load."""
    if os.environ.get(CHAT_SESSION_ENV) == "1":
        return 0
    try:
        payload = json.loads(sys.stdin.read())
        event = payload.get("hook_event_name")
        surface_id = os.environ.get("WMUX_SURFACE_ID")
        root = Path(__file__).resolve().parents[2]
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        _follow_clear(payload, event, surface_id)
        state = EVENT_STATES.get(event)
        if state and surface_id:
            ActivityRecorder().update(root, surface_id, state, now,
                                      prompt_started=(event == "UserPromptSubmit"))
        if surface_id and event in TOOL_EVENTS:
            activity = ToolEventClassifier().classify(payload)
            if activity is not None:
                ActivityRecorder().update(
                    root, surface_id, activity.state, now,
                    activity.last_tool, activity.edited_file)
                if activity.edited_file and surface_id:
                    stamper = BoardOwnerStamper(PaneNameFinder(root, GLOB_PATTERNS))
                    stamper.stamp(activity.edited_file, surface_id)
        if surface_id and event == "UserPromptSubmit":
            handle_prompt(payload, surface_id, root)
        if surface_id and event == "Stop":
            block = handle_stop(payload, surface_id, root)
            if block:
                print(block)
        if surface_id and event == "SessionStart":
            handle_session_start(payload, surface_id, root)
    except Exception:
        _log_error()
    return 0


def _log_error() -> None:
    try:
        ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
        with ERROR_LOG.open("a", encoding="utf-8") as handle:
            handle.write(traceback.format_exc())
    except OSError:
        pass


if __name__ == "__main__":
    raise SystemExit(main())
