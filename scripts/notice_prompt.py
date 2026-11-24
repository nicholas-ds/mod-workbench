"""Parse workbench notice prompts into a board and event tag."""

from __future__ import annotations

import re

NOTICE_PATTERN = re.compile(r"^\[workbench\]\s+board=(\S+)\s+event=(\w+)\.")


class NoticePromptParser:
    """Extract "<board> <event>" from a "[workbench] ..." notice prompt."""

    def parse(self, prompt: str) -> str | None:
        """Return "<board> <event>" for a notice prompt, else None."""
        match = NOTICE_PATTERN.match(prompt.strip())
        if match is None:
            return None
        return f"{match.group(1)} {match.group(2)}"
