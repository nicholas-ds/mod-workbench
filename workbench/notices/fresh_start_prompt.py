"""Build the prompt handed to a fresh session after a restart."""

from __future__ import annotations

from workbench.notices.notice_types import Notice


class FreshStartPrompt:
    """Assemble the fresh-start prompt text. Pure: no clock, no disk."""

    def build(self, handoff_text: str | None, notice: Notice) -> str:
        """Place the handoff under its heading and end with the notice line."""
        lines = ["Fresh session started by the workbench."]
        lines.append("Handoff from the previous session:")
        if handoff_text is None:
            lines.append("No handoff file was found.")
        else:
            lines.append(handoff_text)
        lines.append(notice.line)
        return "\n".join(lines)
