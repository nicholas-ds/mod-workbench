"""Tests: the message writer saves one author message file per id."""

from pathlib import Path

import pytest

from workbench.config import ModConfig
from workbench.message_writer import MessageContext, MessageWriter


def make_cfg(repo: Path) -> ModConfig:
    return ModConfig(name="CityMod", repo=repo, platform=repo, screens=("ui/**/*.swf",),
                     boards=repo, status=repo, tracking=repo, log=repo, briefs=repo,
                     exports=repo)


NOW = "2026-11-07T22:15:00"


def test_writes_file_with_front_matter_and_body(tmp_path: Path) -> None:
    cfg = make_cfg(tmp_path)
    context = MessageContext(view="board", board="layout", item="shot.png",
                             question="layout")
    message_id = MessageWriter().write(cfg.repo, "Make the panel wider", context, NOW)
    file = tmp_path / "messages" / f"{message_id}.md"
    assert message_id == "20261107T221500-1"
    text = file.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "created: '2026-11-07T22:15:00'\n" in text
    assert "view: board\n" in text
    assert "board: layout\n" in text
    assert "item: shot.png\n" in text
    assert "question: layout\n" in text
    assert text.endswith("Make the panel wider\n")


def test_ids_increase_when_file_exists(tmp_path: Path) -> None:
    cfg = make_cfg(tmp_path)
    writer = MessageWriter()
    context = MessageContext(view="home")
    first = writer.write(cfg.repo, "first", context, NOW)
    second = writer.write(cfg.repo, "second", context, NOW)
    assert first == "20261107T221500-1"
    assert second == "20261107T221500-2"
    assert (tmp_path / "messages" / f"{second}.md").read_text(encoding="utf-8").endswith(
        "second\n")


def test_none_context_keys_are_omitted(tmp_path: Path) -> None:
    cfg = make_cfg(tmp_path)
    context = MessageContext(view="home")
    message_id = MessageWriter().write(cfg.repo, "hello", context, NOW)
    text = (tmp_path / "messages" / f"{message_id}.md").read_text(encoding="utf-8")
    assert "view: home\n" in text
    assert "board" not in text
    assert "item" not in text
    assert "question" not in text


def test_empty_text_rejected(tmp_path: Path) -> None:
    cfg = make_cfg(tmp_path)
    writer = MessageWriter()
    for text in ("", "   \n\t "):
        with pytest.raises(ValueError):
            writer.write(cfg.repo, text, MessageContext(view="home"), NOW)
    assert not (tmp_path / "messages").exists()
