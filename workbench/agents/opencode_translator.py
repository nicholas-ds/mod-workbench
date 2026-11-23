"""Translate OpenCode plugin payloads into agent events (Task T1a).

Our own OpenCode plugin posts one JSON object per event. This translator
maps each `type` to an agent state. It is pure: no file, network or clock
access; the caller supplies `now_ms`. Unknown types and payloads without
a session id yield `None`.
"""

from __future__ import annotations

from workbench.agents.agent_event import (
    OPENCODE_SOURCE,
    AgentEvent,
    STATE_ERROR,
    STATE_FINISHED,
    STATE_IDLE,
    STATE_RUNNING,
)

_TOOL_LIMIT = 60


def _base_name(path: str) -> str:
    for separator in ("/", "\\"):
        path = path.rsplit(separator, 1)[-1]
    return path


class OpencodeEventTranslator:
    """Translate one OpenCode plugin payload into one `AgentEvent`."""

    def translate(self, payload: dict, now_ms: int) -> AgentEvent | None:
        session_id = payload.get("session_id", "")
        if not session_id:
            return None
        builder = self._builder_for(payload.get("type", ""))
        if builder is None:
            return None
        return builder(payload, session_id, now_ms)

    def _builder_for(self, event_type: str):
        builders = {
            "session.status": self._translate_status,
            "session.idle": self._translate_idle,
            "session.error": self._translate_error,
            "session.done": self._translate_done,
            "tool.execute.after": self._translate_tool,
            "todo.updated": self._translate_todo,
        }
        return builders.get(event_type)

    def _translate_status(self, payload: dict, session_id: str, now_ms: int) -> AgentEvent | None:
        status = payload.get("status", "")
        if status in ("busy", "retry"):
            state = STATE_RUNNING
        elif status == "idle":
            state = STATE_IDLE
        else:
            return None
        return self._event(payload, session_id, now_ms, state)

    def _translate_idle(self, payload: dict, session_id: str, now_ms: int) -> AgentEvent | None:
        return self._event(payload, session_id, now_ms, STATE_IDLE)

    def _translate_error(self, payload: dict, session_id: str, now_ms: int) -> AgentEvent | None:
        return self._event(payload, session_id, now_ms, STATE_ERROR)

    def _translate_done(self, payload: dict, session_id: str, now_ms: int) -> AgentEvent | None:
        return self._event(payload, session_id, now_ms, STATE_FINISHED)

    def _translate_tool(self, payload: dict, session_id: str, now_ms: int) -> AgentEvent | None:
        tool = payload.get("tool", "")[:_TOOL_LIMIT]
        return self._event(
            payload, session_id, now_ms, STATE_RUNNING,
            last_tool=tool,
            last_file=_base_name(payload.get("file", "")),
            counts_tool=True,
        )

    def _translate_todo(self, payload: dict, session_id: str, now_ms: int) -> AgentEvent | None:
        return self._event(payload, session_id, now_ms, STATE_RUNNING,
                           progress=payload.get("progress", ""))

    def _event(self, payload: dict, session_id: str, now_ms: int, state: str,
               last_tool: str = "", last_file: str = "",
               counts_tool: bool = False, progress: str = "") -> AgentEvent:
        return AgentEvent(
            source=OPENCODE_SOURCE,
            agent_id=session_id,
            at_ms=now_ms,
            state=state,
            parent_id=payload.get("parent_id", ""),
            cwd=payload.get("directory", ""),
            title=payload.get("title", ""),
            last_tool=last_tool,
            last_file=last_file,
            progress=progress,
            counts_tool=counts_tool,
        )
