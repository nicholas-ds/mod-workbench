"""Tests for the board HTTP API: list, detail, answers, lifecycle and notes."""

import json
from pathlib import Path

from api_fixtures import (
    ANSWERS_URL,
    BAD_BOARD,
    COLOR_BOARD,
    LAYOUT_BOARD,
    make_client,
    make_mod_repo,
    write_board,
)


def test_boards_list_blocking_first(tmp_path: Path) -> None:
    repo = make_mod_repo(tmp_path)
    write_board(repo, "aa-color", COLOR_BOARD)
    write_board(repo, "zz-layout", LAYOUT_BOARD)
    client = make_client(tmp_path)
    body = client.get("/api/mods/CityMod/boards?state=open").json()
    assert {"id", "title", "raised_by", "created", "tags", "blocking"} <= set(
        body["table"]["columns"])
    assert [row["id"] for row in body["table"]["rows"]] == ["zz-layout", "aa-color"]
    assert body["table"]["rows"][0]["blocking"] is True
    assert body["table"]["rows"][1]["blocking"] is False
    mods = client.get("/api/mods").json()
    row = next(row for row in mods["rows"] if row.get("name") == "CityMod")
    assert row["open_boards"] == 2


def test_board_detail_has_item_urls_and_kinds(tmp_path: Path) -> None:
    repo = make_mod_repo(tmp_path)
    folder = write_board(repo, "layout", LAYOUT_BOARD)
    (folder / "shot.png").write_bytes(b"\x89PNG\r\n")
    (folder / "diagram.html").write_text("<p>hi</p>", encoding="utf-8")
    body = make_client(tmp_path).get("/api/mods/CityMod/boards/layout").json()
    items = body["items"]
    assert items[0]["url"].startswith("/api/mods/CityMod/boards/layout/items/shot.png?v=")
    assert items[0]["kind"] == "image"
    assert items[1]["url"].startswith("/api/mods/CityMod/boards/layout/items/diagram.html?v=")
    assert items[1]["kind"] == "html"
    assert body["answers"] == []
    assert body["questions"][0]["id"] == "layout"


def test_answer_saves_json(tmp_path: Path) -> None:
    repo = make_mod_repo(tmp_path)
    write_board(repo, "layout", LAYOUT_BOARD)
    response = make_client(tmp_path).post(
        ANSWERS_URL,
        json={"question_id": "layout", "picked": "wide", "text": None,
              "comment": "wide reads better"})
    assert response.status_code == 200
    path = repo / "boards" / "open" / "layout" / "answers.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    answer = data["answers"][0]
    assert answer["question_id"] == "layout"
    assert answer["picked"] == "wide"
    assert answer["comment"] == "wide reads better"
    assert answer["answered_at"]


def test_answer_unknown_option_is_400(tmp_path: Path) -> None:
    repo = make_mod_repo(tmp_path)
    write_board(repo, "layout", LAYOUT_BOARD)
    response = make_client(tmp_path).post(
        ANSWERS_URL, json={"question_id": "layout", "picked": "nope"})
    assert response.status_code == 400
    assert not (repo / "boards" / "open" / "layout" / "answers.json").exists()


def test_answer_unknown_question_is_400(tmp_path: Path) -> None:
    make_mod_repo(tmp_path)
    write_board(tmp_path / "CityMod", "layout", LAYOUT_BOARD)
    response = make_client(tmp_path).post(
        ANSWERS_URL, json={"question_id": "nope", "picked": "wide"})
    assert response.status_code == 400


def test_answer_unknown_board_is_404(tmp_path: Path) -> None:
    make_mod_repo(tmp_path)
    response = make_client(tmp_path).post(
        "/api/mods/CityMod/boards/ghost/answers",
        json={"question_id": "layout", "picked": "wide"})
    assert response.status_code == 404


def test_close_moves_to_done(tmp_path: Path) -> None:
    repo = make_mod_repo(tmp_path)
    write_board(repo, "layout", LAYOUT_BOARD)
    client = make_client(tmp_path)
    response = client.post("/api/mods/CityMod/boards/layout/close")
    assert response.status_code == 200
    assert (repo / "boards" / "done" / "layout" / "board.md").is_file()
    assert not (repo / "boards" / "open" / "layout").exists()
    body = client.get("/api/mods/CityMod/boards?state=done").json()
    assert [row["id"] for row in body["table"]["rows"]] == ["layout"]


def test_reopen_non_default_writes_rework_brief(tmp_path: Path) -> None:
    repo = make_mod_repo(tmp_path)
    write_board(repo, "layout", LAYOUT_BOARD)
    client = make_client(tmp_path)
    client.post(ANSWERS_URL, json={"question_id": "layout", "picked": "wide"})
    client.post("/api/mods/CityMod/boards/layout/close")
    response = client.post("/api/mods/CityMod/boards/layout/reopen")
    assert response.status_code == 200
    assert (repo / "boards" / "open" / "layout" / "board.md").is_file()
    brief = (repo / "briefs" / "rework-layout.md").read_text(encoding="utf-8")
    assert "queue/swf" in brief
    assert "rework layout" in (repo / "LOG.md").read_text(encoding="utf-8")


def test_note_writes_file(tmp_path: Path) -> None:
    repo = make_mod_repo(tmp_path)
    folder = write_board(repo, "layout", LAYOUT_BOARD)
    (folder / "shot.png").write_bytes(b"png")
    response = make_client(tmp_path).post(
        "/api/mods/CityMod/boards/layout/notes",
        json={"item": "shot.png", "x": 12.5, "y": 40.0, "text": "look here"})
    assert response.status_code == 200
    text = (repo / "notes" / "layout-1.md").read_text(encoding="utf-8")
    assert "x: 12.5" in text
    assert "look here" in text


def test_bad_board_shows_error_row(tmp_path: Path) -> None:
    repo = make_mod_repo(tmp_path)
    write_board(repo, "good", COLOR_BOARD)
    write_board(repo, "bad", BAD_BOARD)
    body = make_client(tmp_path).get("/api/mods/CityMod/boards?state=open").json()
    rows = body["table"]["rows"]
    assert any(row.get("error") for row in rows)
    assert any(row.get("id") == "good" for row in rows)


def test_bad_mod_does_not_hide_good_mod(tmp_path: Path) -> None:
    make_mod_repo(tmp_path)
    broken = tmp_path / "Broken"
    broken.mkdir()
    (broken / "workbench.toml").write_text("", encoding="utf-8")
    body = make_client(tmp_path).get("/api/mods").json()
    rows = body["rows"]
    assert any(row.get("name") == "CityMod" for row in rows)
    assert any(row.get("error") for row in rows)
