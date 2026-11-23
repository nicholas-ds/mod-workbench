"""Tests: the message reader lists author message files newest first."""

from pathlib import Path

from workbench.core.config import ModConfig
from workbench.mods.message_reader import MessageReader
from workbench.panes.message_writer import MessageContext, MessageWriter


def make_cfg(repo: Path) -> ModConfig:
    return ModConfig(name="CityMod", repo=repo, platform=repo, screens=("ui/**/*.swf",),
                     boards=repo, status=repo, tracking=repo, log=repo, briefs=repo,
                     exports=repo)


def test_reads_messages_newest_first_with_fields(tmp_path: Path) -> None:
    cfg = make_cfg(tmp_path)
    writer = MessageWriter()
    writer.write(cfg.repo, "first", MessageContext(view="home", item="shot.png",
                                              question="q1"), "2026-11-07T10:00:00")
    writer.write(cfg.repo, "second", MessageContext(view="board", board="layout"),
                 "2026-11-08T11:00:00")
    records = MessageReader().read_all(cfg.repo)
    assert [record.id for record in records] == ["20261108T110000-1",
                                                 "20261107T100000-1"]
    assert [record.text for record in records] == ["second", "first"]
    assert records[0].view == "board"
    assert records[0].board == "layout"
    assert records[0].item is None
    assert records[0].question is None
    assert records[1].view == "home"
    assert records[1].item == "shot.png"
    assert records[1].question == "q1"
    assert records[0].created == "2026-11-08T11:00:00"
    assert records[0].reply is None
    assert records[0].done is False


def test_reads_done_folder_and_reply_file(tmp_path: Path) -> None:
    cfg = make_cfg(tmp_path)
    writer = MessageWriter()
    message_id = writer.write(cfg.repo, "handle me", MessageContext(view="home"),
                              "2026-11-07T10:00:00")
    replies = tmp_path / "messages" / "replies"
    replies.mkdir()
    (replies / f"{message_id}.md").write_text("Done, widened.\n", encoding="utf-8")
    done = tmp_path / "messages" / "done"
    done.mkdir()
    (tmp_path / "messages" / f"{message_id}.md").rename(done / f"{message_id}.md")
    records = MessageReader().read_all(cfg.repo)
    assert len(records) == 1
    record = records[0]
    assert record.done is True
    assert record.reply == "Done, widened."
    assert record.text == "handle me"


def test_empty_messages_folder_gives_no_records(tmp_path: Path) -> None:
    cfg = make_cfg(tmp_path)
    assert MessageReader().read_all(cfg.repo) == ()
