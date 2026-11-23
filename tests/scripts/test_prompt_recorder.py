import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from prompt_recorder import CliPromptRecorder
from workbench.mods.message_reader import MessageReader

NOW = datetime(2026, 11, 8, 12, 30, 0, tzinfo=timezone.utc)


def test_cli_prompt_becomes_a_readable_message(tmp_path: Path) -> None:
    path = CliPromptRecorder().record(tmp_path, "hello there", NOW)
    assert path is not None and path.name == "20261108T123000+0000-1.md"
    record = MessageReader().read_all(tmp_path)[0]
    assert (record.text, record.view, record.done) == ("hello there", "cli", False)


def test_workbench_and_system_prompts_are_skipped(tmp_path: Path) -> None:
    recorder = CliPromptRecorder()
    assert recorder.record(tmp_path, "[workbench] mod=x | hi", NOW) is None
    assert recorder.record(tmp_path, "<task-notification>x", NOW) is None
    assert recorder.record(tmp_path, "   ", NOW) is None


def test_same_second_gets_next_number(tmp_path: Path) -> None:
    recorder = CliPromptRecorder()
    recorder.record(tmp_path, "a", NOW)
    second = recorder.record(tmp_path, "b", NOW)
    assert second is not None and second.name.endswith("-2.md")


def test_existing_name_is_not_overwritten(tmp_path: Path) -> None:
    messages = tmp_path / "messages"
    messages.mkdir()
    first = messages / "20261108T123000+0000-1.md"
    first.write_text("original", encoding="utf-8")
    path = CliPromptRecorder().record(tmp_path, "new text", NOW)
    assert path is not None and path.name.endswith("-2.md")
    assert first.read_text(encoding="utf-8") == "original"
