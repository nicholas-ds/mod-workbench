"""Turn a composed handoff block into one chat event that shows what was passed on."""

from __future__ import annotations

import re

from workbench.chat_event import KIND_HANDOFF, ChatEvent

_FROM = re.compile(r"switched this chat from (.+?) to you\.")
_PATH_PREFIX = "Full transcript: "
_TAIL_HEADER = "Last messages, oldest first:"
_CLOSE = "[/handoff]"
_PARAGRAPH = "\n\n"
_QUOTE_GAP = "\n>\n"
_SHOWN_MESSAGES = 4
_SHOWN_CHARS = 200
_SPEAKER = re.compile(r"^\[[^\]]+\] ")


class HandoffNoticeBuilder:
    """Read a handoff block and write the Markdown card the chat shows."""

    def build(self, block: str) -> ChatEvent:
        lines = block.split("\n")
        source = self._source_of(block)
        path = self._path_of(lines)
        shared = self._messages(self._shared_lines(lines))
        text = self._markdown(source, path, shared)
        return ChatEvent(kind=KIND_HANDOFF, text=text, detail=path)

    def _source_of(self, block: str) -> str:
        found = _FROM.search(block)
        return found.group(1) if found else "the other agent"

    def _path_of(self, lines: list[str]) -> str:
        for line in lines:
            if line.startswith(_PATH_PREFIX):
                return line[len(_PATH_PREFIX):].strip()
        return ""

    def _shared_lines(self, lines: list[str]) -> list[str]:
        if _TAIL_HEADER not in lines:
            return []
        start = lines.index(_TAIL_HEADER) + 1
        end = lines.index(_CLOSE) if _CLOSE in lines else len(lines)
        return [line for line in lines[start:end] if line.strip()]

    def _messages(self, lines: list[str]) -> list[str]:
        """Group continuation lines under the message that opened them."""
        messages: list[str] = []
        for line in lines:
            if _SPEAKER.match(line) or not messages:
                messages.append(line)
            else:
                messages[-1] = f"{messages[-1]} {line.strip()}"
        return messages

    def _markdown(self, source: str, path: str, shared: list[str]) -> str:
        head = f"**Handoff from {source}.** The last {len(shared)} messages were passed on."
        parts = [head, f"Transcript: `{path}`"] if path else [head]
        shown = [self._capped(message) for message in shared[-_SHOWN_MESSAGES:]]
        if shown:
            parts.append(_QUOTE_GAP.join(f"> {message}" for message in shown))
        return _PARAGRAPH.join(parts)

    def _capped(self, message: str) -> str:
        if len(message) <= _SHOWN_CHARS:
            return message
        return message[:_SHOWN_CHARS].rstrip() + "..."
