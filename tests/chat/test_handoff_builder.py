"""Tests for HandoffBuilder: transcript file plus handoff block."""

from pathlib import Path

from workbench.chat.chat_event import KIND_TEXT, KIND_THINKING, KIND_USER, ChatEvent
from workbench.chat.handoff_builder import HandoffBuilder
from workbench.chat.handoff_composer import HandoffComposer
from workbench.chat.transcript_writer import TranscriptWriter


def _builder(directory: Path) -> HandoffBuilder:
    return HandoffBuilder(HandoffComposer(), TranscriptWriter(directory))


def test_no_user_or_text_events_gives_empty_string_and_no_file(tmp_path: Path) -> None:
    events = [ChatEvent(kind=KIND_THINKING, text="thinking out loud")]
    block = _builder(tmp_path / "transcripts").build(
        "Workbench~t3", "Claude", events)
    assert block == ""
    assert not (tmp_path / "transcripts").exists()


def test_build_names_the_transcript_file_that_exists(tmp_path: Path) -> None:
    directory = tmp_path / "transcripts"
    events = [
        ChatEvent(kind=KIND_USER, text="fix the dock"),
        ChatEvent(kind=KIND_TEXT, text="done, tests pass"),
    ]
    block = _builder(directory).build("Workbench~t3", "Claude", events)
    lines = block.splitlines()
    assert lines[0].startswith("[handoff]")
    assert lines[-1] == "[/handoff]"
    assert "Workbench_t3" in block
    path = Path(_transcript_line(block).removeprefix("Full transcript: "))
    assert path.is_file()
    assert "[Author] fix the dock" in path.read_text(encoding="utf-8")


def _transcript_line(block: str) -> str:
    for line in block.splitlines():
        if line.startswith("Full transcript: "):
            return line
    raise AssertionError("block names no transcript file")
