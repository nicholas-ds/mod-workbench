"""Classify hook payloads into a tool activity state and a tool label."""

from __future__ import annotations

import re
from dataclasses import dataclass

WORKER_PATTERN = re.compile(r"session\.ps1\s+(send|wait)|opencode")
DETAIL_KEYS = ("command", "file_path", "description", "pattern", "url")
EDIT_TOOLS = ("Edit", "Write", "MultiEdit", "NotebookEdit")
EDIT_PATH_KEYS = ("file_path", "notebook_path")
TOOL_DETAIL_LIMIT = 60
MESSAGE_LIMIT = 80


@dataclass(frozen=True)
class ToolActivity:
    state: str
    last_tool: str
    edited_file: str = ""
    edited_path: str = ""


class ToolEventClassifier:
    """Turn one hook payload into a ToolActivity, or None for other events."""

    def classify(self, payload: dict) -> ToolActivity | None:
        event = payload.get("hook_event_name")
        if event == "PreToolUse":
            return self._classify_tool_use(payload)
        if event == "Notification":
            return self._classify_notification(payload)
        return None

    def _classify_tool_use(self, payload: dict) -> ToolActivity:
        tool_name = payload.get("tool_name", "")
        tool_input = payload.get("tool_input") or {}
        detail = self._first_detail(tool_input)
        last_tool = f"{tool_name} {detail}".strip()
        state = "worker" if self._is_worker(tool_name, tool_input) else "working"
        edited_path = self._edited_path(tool_name, tool_input)
        return ToolActivity(state=state, last_tool=self._toml_safe(last_tool),
                            edited_file=self._toml_safe(self._base_name(edited_path)),
                            edited_path=edited_path)

    def _classify_notification(self, payload: dict) -> ToolActivity:
        message = payload.get("message", "")
        return ToolActivity(state="needs-you", last_tool=self._toml_safe(message[:MESSAGE_LIMIT]))

    def _first_detail(self, tool_input: dict) -> str:
        for key in DETAIL_KEYS:
            value = tool_input.get(key)
            if isinstance(value, str) and value:
                return self._one_line(value)[:TOOL_DETAIL_LIMIT]
        return ""

    def _edited_path(self, tool_name: str, tool_input: dict) -> str:
        if tool_name not in EDIT_TOOLS:
            return ""
        for key in EDIT_PATH_KEYS:
            value = tool_input.get(key)
            if isinstance(value, str) and value:
                return value
        return ""

    def _base_name(self, path: str) -> str:
        return path.replace("\\", "/").rsplit("/", 1)[-1]

    def _is_worker(self, tool_name: str, tool_input: dict) -> bool:
        if tool_name in ("Agent", "Task"):
            return True
        if tool_name == "Bash":
            command = tool_input.get("command", "")
            return bool(WORKER_PATTERN.search(command))
        return False

    def _one_line(self, text: str) -> str:
        for newline in ("\r\n", "\n", "\r"):
            text = text.replace(newline, " ")
        return text

    def _toml_safe(self, text: str) -> str:
        text = text.replace("\\", "/").replace('"', " ")
        return "".join(char if char.isprintable() else " " for char in text)
