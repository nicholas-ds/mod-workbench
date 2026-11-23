"""The note that tells a chat agent it runs inside the workbench app."""

from __future__ import annotations


class ChatSessionNote:
    """Build the system prompt note for one named app chat."""

    def text(self, name: str) -> str:
        return "\n".join(
            [
                f'You run inside the mod workbench app chat named "{name}".',
                f"- When you raise a workbench board, set `raised_by: chat-{name}` "
                "in its front matter. The answer then comes back to this chat as "
                'a message that starts with "[workbench board]".',
                '- Do not write a reply file for a "[workbench board]" message. '
                "Act on it and answer here.",
                "- Surface work upfront, unasked: put your plan, designs, "
                "findings and open items on a board in the same turn. "
                "Rule: E:/repos/mods/AGENTS.md, Surface work upfront.",
                "- The AskUserQuestion tool is not available. Ask the author "
                "through a workbench board.",
            ]
        )
