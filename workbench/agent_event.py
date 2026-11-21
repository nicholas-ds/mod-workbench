"""Agent event type shared by all worker event translators (Task T1a).

A translator turns one raw JSON payload from an agent (Claude Code hook or
OpenCode plugin) into an `AgentEvent`, or returns `None` when the payload
does not describe a known event. The type is frozen; translators are pure.
"""

from __future__ import annotations

from dataclasses import dataclass

CLAUDE_SOURCE = "claude"
OPENCODE_SOURCE = "opencode"

STATE_RUNNING = "running"
STATE_IDLE = "idle"
STATE_NEEDS_YOU = "needs-you"
STATE_ERROR = "error"
STATE_FINISHED = "finished"


@dataclass(frozen=True)
class AgentEvent:
    source: str
    agent_id: str
    at_ms: int
    state: str
    parent_id: str = ""
    cwd: str = ""
    title: str = ""
    last_tool: str = ""
    last_file: str = ""
    progress: str = ""
    counts_tool: bool = False
