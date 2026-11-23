"""Strip workbench-injected lines from user text shown in chat."""

from __future__ import annotations


class UserTextCleaner:
    """Remove the dock context line from shown user text.

    ``CONTEXT_PREFIX`` starts the line the web dock prepends to an SDK
    prompt; ``web/message_dock.js`` writes the same prefix.
    """

    CONTEXT_PREFIX = "(The author is looking at board "
    NEWLINE = "\n"

    def clean(self, text: str) -> str:
        kept = [
            line
            for line in text.split(self.NEWLINE)
            if not line.strip().startswith(self.CONTEXT_PREFIX)
        ]
        return self.NEWLINE.join(kept).strip()
