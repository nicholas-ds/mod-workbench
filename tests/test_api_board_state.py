"""Tests: board detail reports its state, and lifecycle calls reject the wrong state."""

from pathlib import Path

import pytest

from api_fixtures import ANSWERS_URL, LAYOUT_BOARD, make_client, make_mod_repo, write_board
from test_board_notifier import RecordingSender

BOARD_URL = "/api/mods/CityMod/boards/layout"


def test_get_board_finds_done_board_with_state(tmp_path: Path) -> None:
    repo = make_mod_repo(tmp_path)
    write_board(repo, "layout", LAYOUT_BOARD)
    client = make_client(tmp_path)
    assert client.get(BOARD_URL).json()["state"] == "open"
    client.post(f"{BOARD_URL}/close")
    body = client.get(BOARD_URL).json()
    assert body["state"] == "done"
    assert (repo / "boards" / "done" / "layout" / "board.md").is_file()


def test_answer_on_done_board_is_409(tmp_path: Path) -> None:
    repo = make_mod_repo(tmp_path)
    write_board(repo, "layout", LAYOUT_BOARD)
    client = make_client(tmp_path)
    client.post(f"{BOARD_URL}/close")
    response = client.post(ANSWERS_URL, json={"question_id": "layout", "picked": "wide"})
    assert response.status_code == 409
    assert not (repo / "boards" / "done" / "layout" / "answers.json").exists()


def test_close_twice_is_409(tmp_path: Path) -> None:
    make_mod_repo(tmp_path)
    write_board(tmp_path / "CityMod", "layout", LAYOUT_BOARD)
    client = make_client(tmp_path)
    assert client.post(f"{BOARD_URL}/close").status_code == 200
    assert client.post(f"{BOARD_URL}/close").status_code == 409


def test_reopen_open_board_is_409(tmp_path: Path) -> None:
    make_mod_repo(tmp_path)
    write_board(tmp_path / "CityMod", "layout", LAYOUT_BOARD)
    client = make_client(tmp_path)
    assert client.post(f"{BOARD_URL}/reopen").status_code == 409
    assert (tmp_path / "CityMod" / "boards" / "open" / "layout" / "board.md").is_file()


def test_close_response_reports_notified(tmp_path: Path,
                                         monkeypatch: pytest.MonkeyPatch) -> None:
    repo = make_mod_repo(tmp_path)
    write_board(repo, "layout", LAYOUT_BOARD)
    status = repo / "status.toml"
    status.unlink()
    status.mkdir()
    (status / "build.toml").write_text('wmux_surface = "surf-1"', encoding="utf-8")
    sender = RecordingSender()
    monkeypatch.setattr("workbench.api.PaneSender", lambda: sender)
    body = make_client(tmp_path).post(f"{BOARD_URL}/close").json()
    assert body["notified"] is True
    assert sender.lines != []


def test_send_response_reports_notified(tmp_path: Path,
                                        monkeypatch: pytest.MonkeyPatch) -> None:
    repo = make_mod_repo(tmp_path)
    write_board(repo, "layout", LAYOUT_BOARD)
    status = repo / "status.toml"
    status.unlink()
    status.mkdir()
    (status / "build.toml").write_text('wmux_surface = "surf-1"', encoding="utf-8")
    sender = RecordingSender()
    monkeypatch.setattr("workbench.api.PaneSender", lambda: sender)
    body = make_client(tmp_path).post(f"{BOARD_URL}/send").json()
    assert body == {"id": "layout", "notified": True}


def test_note_response_reports_notified(tmp_path: Path,
                                        monkeypatch: pytest.MonkeyPatch) -> None:
    repo = make_mod_repo(tmp_path)
    folder = write_board(repo, "layout", LAYOUT_BOARD)
    (folder / "shot.png").write_bytes(b"png")
    status = repo / "status.toml"
    status.unlink()
    status.mkdir()
    (status / "build.toml").write_text('wmux_surface = "surf-1"', encoding="utf-8")
    sender = RecordingSender()
    monkeypatch.setattr("workbench.api.PaneSender", lambda: sender)
    body = make_client(tmp_path).post(
        f"{BOARD_URL}/notes",
        json={"item": "shot.png", "x": 0.5, "y": 0.25, "text": "look here"}).json()
    assert body["file"] == "layout-1.md"
    assert body["notified"] is True
    assert "event=note" in sender.lines[0]
