import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from stop_gate import ReplyCapturer, StopGate, TranscriptReader, Workspace, WorkspaceLocator


def make_repo(tmp_path: Path, status: str = 'wmux_surface = "s1"\n') -> Workspace:
    repo = tmp_path / "repo"
    (repo / "status").mkdir(parents=True)
    status_file = repo / "status" / "a.toml"
    status_file.write_text(status, encoding="utf-8")
    return Workspace(repo, status_file)


def test_locator_finds_workspace_by_surface(tmp_path: Path) -> None:
    workspace = make_repo(tmp_path)
    assert WorkspaceLocator().locate(tmp_path, "s1") == workspace
    assert WorkspaceLocator().locate(tmp_path, "other") is None


def test_gate_blocks_without_board_or_finished_phase(tmp_path: Path) -> None:
    assert StopGate().may_stop(make_repo(tmp_path)) is False


def test_gate_allows_an_open_board(tmp_path: Path) -> None:
    workspace = make_repo(tmp_path)
    (workspace.repo / "boards" / "open" / "b1").mkdir(parents=True)
    assert StopGate().may_stop(workspace) is True


def test_gate_blocks_when_only_board_is_permanent(tmp_path: Path) -> None:
    workspace = make_repo(tmp_path)
    folder = workspace.repo / "boards" / "open" / "mod-status"
    folder.mkdir(parents=True)
    (folder / "board.md").write_text(
        "---\ntitle: s\ntags: [permanent]\nquestions: []\n---\n", encoding="utf-8")
    assert StopGate().may_stop(workspace) is False


def test_gate_allows_a_non_permanent_board(tmp_path: Path) -> None:
    workspace = make_repo(tmp_path)
    folder = workspace.repo / "boards" / "open" / "b1"
    folder.mkdir(parents=True)
    (folder / "board.md").write_text(
        "---\ntitle: b\ntags: [screen]\nquestions: []\n---\n", encoding="utf-8")
    assert StopGate().may_stop(workspace) is True


def test_gate_blocks_when_tags_mix_screen_and_permanent(tmp_path: Path) -> None:
    workspace = make_repo(tmp_path)
    folder = workspace.repo / "boards" / "open" / "ui-atlas"
    folder.mkdir(parents=True)
    (folder / "board.md").write_text(
        "---\ntitle: a\ntags: [screen, permanent]\nquestions: []\n---\n", encoding="utf-8")
    assert StopGate().may_stop(workspace) is False


def test_gate_allows_finished_phase(tmp_path: Path) -> None:
    workspace = make_repo(tmp_path, 'wmux_surface = "s1"\nphase = "finished"\n')
    assert StopGate().may_stop(workspace) is True


def test_finished_phase_with_extra_spacing_matches(tmp_path: Path) -> None:
    workspace = make_repo(tmp_path, 'wmux_surface = "s1"\n  phase  =  "finished"  \n')
    assert StopGate().may_stop(workspace) is True


def test_capturer_writes_reply_and_moves_message(tmp_path: Path) -> None:
    workspace = make_repo(tmp_path)
    messages = workspace.repo / "messages"
    messages.mkdir()
    (messages / "m1.md").write_text("hi", encoding="utf-8")
    assert ReplyCapturer().capture(workspace.repo, "answer") == 1
    assert (messages / "replies" / "m1.md").read_text(encoding="utf-8") == "answer\n"
    assert (messages / "done" / "m1.md").exists()


def test_capturer_keeps_an_existing_reply(tmp_path: Path) -> None:
    workspace = make_repo(tmp_path)
    messages = workspace.repo / "messages"
    (messages / "replies").mkdir(parents=True)
    (messages / "m1.md").write_text("hi", encoding="utf-8")
    (messages / "replies" / "m1.md").write_text("mine\n", encoding="utf-8")
    ReplyCapturer().capture(workspace.repo, "other")
    assert (messages / "replies" / "m1.md").read_text(encoding="utf-8") == "mine\n"


def test_locked_message_is_skipped_and_others_still_move(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workspace = make_repo(tmp_path)
    messages = workspace.repo / "messages"
    messages.mkdir()
    (messages / "a.md").write_text("a", encoding="utf-8")
    (messages / "b.md").write_text("b", encoding="utf-8")
    real_replace = Path.replace

    def flaky_replace(self: Path, target: Path) -> Path:
        if self.name == "a.md":
            raise OSError("locked by UI")
        return real_replace(self, target)

    monkeypatch.setattr(Path, "replace", flaky_replace)
    assert ReplyCapturer().capture(workspace.repo, "answer") == 2
    assert (messages / "a.md").exists()
    assert (messages / "done" / "b.md").exists()


def test_reader_returns_last_assistant_text(tmp_path: Path) -> None:
    lines = [
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "first"}]}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "last"}]}},
        {"type": "user", "message": {"content": "x"}},
    ]
    transcript = tmp_path / "t.jsonl"
    transcript.write_text("\n".join(json.dumps(line) for line in lines), encoding="utf-8")
    assert TranscriptReader().last_assistant_text(transcript) == "last"


def test_reader_reads_tail_of_a_large_transcript(tmp_path: Path) -> None:
    filler = json.dumps({"type": "user", "message": {"content": "x" * 64}})
    lines = [filler] * 2000
    lines.append(json.dumps(
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "tail text"}]}}))
    transcript = tmp_path / "big.jsonl"
    transcript.write_text("\n".join(lines), encoding="utf-8")
    assert transcript.stat().st_size > 64 * 1024
    assert TranscriptReader().last_assistant_text(transcript) == "tail text"


def test_capturer_keeps_an_unprompted_reply_once(tmp_path: Path) -> None:
    workspace = make_repo(tmp_path)
    assert ReplyCapturer().capture(workspace.repo, "update") == 0
    ReplyCapturer().capture(workspace.repo, "update")
    messages = workspace.repo / "messages"
    replies = list((messages / "replies").glob("*-agent.md"))
    assert [path.read_text(encoding="utf-8") for path in replies] == ["update\n"]
    assert len(list((messages / "done").glob("*-agent.md"))) == 1
