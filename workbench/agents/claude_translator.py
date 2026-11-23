"""Translate Claude Code hook payloads into agent events (Task T1a).

Claude Code posts one JSON object per HTTP hook call. This translator maps
each `hook_event_name` to an agent state. It is pure: no file, network or
clock access; the caller supplies `now_ms`. Unknown events and payloads
without a session id yield `None`.
"""

from __future__ import annotations

from workbench.agents.agent_event import (
    AgentEvent,
    CLAUDE_SOURCE,
    STATE_ERROR,
    STATE_FINISHED,
    STATE_IDLE,
    STATE_NEEDS_YOU,
    STATE_RUNNING,
)

from workbench.core.tool_input_detail import first_input_detail

_FILE_TOOLS = frozenset({"Edit", "Write", "MultiEdit", "NotebookEdit"})


def _base_name(path: str) -> str:
    for separator in ("/", "\\"):
        path = path.rsplit(separator, 1)[-1]
    return path


def _tool_file_name(tool_input: dict) -> str:
    for key in ("file_path", "notebook_path"):
        path = tool_input.get(key, "")
        if isinstance(path, str) and path:
            return _base_name(path)
    return ""


class ClaudeEventTranslator:
    """Translate one Claude Code hook payload into one `AgentEvent`."""

    def translate(self, payload: dict, now_ms: int) -> AgentEvent | None:
        session_id = payload.get("session_id", "")
        if not session_id:
            return None
        event_name = payload.get("hook_event_name", "")
        state = self._state_for(event_name)
        if state is None:
            return None
        agent_id = payload.get("agent_id") or session_id
        if event_name in ("SubagentStart", "SubagentStop"):
            agent_id = payload.get("agent_id", "")
            if not agent_id:
                return None
        tool_input = payload.get("tool_input") or {}
        if not isinstance(tool_input, dict):
            tool_input = {}
        return AgentEvent(
            source=CLAUDE_SOURCE,
            agent_id=agent_id,
            at_ms=now_ms,
            state=state,
            parent_id=self._parent_id(event_name, session_id),
            cwd=payload.get("cwd", ""),
            title=payload.get("agent_type", "") if event_name == "SubagentStart" else "",
            last_tool=self._last_tool(event_name, payload, tool_input),
            last_file=self._last_file(event_name, payload, tool_input),
            counts_tool=event_name == "PreToolUse",
        )

    def _state_for(self, event_name: str) -> str | None:
        states = {
            "UserPromptSubmit": STATE_RUNNING,
            "PreToolUse": STATE_RUNNING,
            "PermissionRequest": STATE_NEEDS_YOU,
            "SubagentStart": STATE_RUNNING,
            "SubagentStop": STATE_FINISHED,
            "Stop": STATE_IDLE,
            "StopFailure": STATE_ERROR,
            "SessionEnd": STATE_FINISHED,
        }
        return states.get(event_name)

    def _parent_id(self, event_name: str, session_id: str) -> str:
        return session_id if event_name == "SubagentStart" else ""

    def _last_tool(self, event_name: str, payload: dict, tool_input: dict) -> str:
        if event_name == "PreToolUse":
            tool_name = payload.get("tool_name", "")
            detail = first_input_detail(tool_input)
            return f"{tool_name} {detail}".strip()
        if event_name == "PermissionRequest":
            return payload.get("tool_name", "")
        return ""

    def _last_file(self, event_name: str, payload: dict, tool_input: dict) -> str:
        if payload.get("tool_name") in _FILE_TOOLS:
            return _tool_file_name(tool_input)
        return ""
