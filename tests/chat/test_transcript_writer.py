"""Tests for TranscriptWriter: the markdown transcript file of one chat."""

from pathlib import Path

from workbench.chat.chat_event import KIND_TEXT, KIND_THINKING, KIND_TOOL, KIND_USER, ChatEvent
from workbench.chat.transcript_writer import TranscriptWriter


def _user(text: str) -> ChatEvent:
    return ChatEvent(kind=KIND_USER, text=text)


def _assistant(text: str) -> ChatEvent:
    return ChatEvent(kind=KIND_TEXT, text=text)


def test_writes_safe_named_file_under_directory(tmp_path: Path) -> None:
    directory = tmp_path / "transcripts"
    path = TranscriptWriter(directory).write(
        "Workbench~t3", [_user("start the build")])
    assert path == (directory / "Workbench_t3.md").resolve()
    assert path.is_absolute()
    assert path.is_file()


def test_content_has_both_speakers_separated_by_blank_lines(tmp_path: Path) -> None:
    events = [_user("fix the dock"), _assistant("done, tests pass")]
    path = TranscriptWriter(tmp_path).write("Workbench~t3", events)
    content = path.read_text(encoding="utf-8")
    assert content == "[Author] fix the dock\n\n[Assistant] done, tests pass"


def test_keeps_only_user_and_text_events(tmp_path: Path) -> None:
    events = [
        _user("fix the dock"),
        ChatEvent(kind=KIND_THINKING, text="hmm"),
        _assistant("done"),
        ChatEvent(kind=KIND_TOOL, text="Bash", tool_name="Bash", detail="pytest"),
    ]
    path = TranscriptWriter(tmp_path).write("Workbench~t3", events)
    content = path.read_text(encoding="utf-8")
    assert "[Author] fix the dock" in content
    assert "[Assistant] done" in content
    assert "hmm" not in content
    assert "Bash" not in content


def test_second_write_overwrites(tmp_path: Path) -> None:
    writer = TranscriptWriter(tmp_path)
    writer.write("Workbench~t3", [_user("first text")])
    path = writer.write("Workbench~t3", [_user("second text")])
    content = path.read_text(encoding="utf-8")
    assert "first text" not in content
    assert "second text" in content
