"""Tests for `GET /api/overview`: tasks per mod from the master tracking file."""

from datetime import date
from pathlib import Path

from api_fixtures import make_client, make_mod_repo


def test_overview_returns_repos_from_master_file(tmp_path: Path) -> None:
    make_mod_repo(tmp_path)
    today = date.today().isoformat()
    (tmp_path / "tracking.md").write_text(
        "## CityMod\n"
        f"updated: {today}\n"
        "- [ ] write docs. waits: author, board: docs-q\n"
        "- [x] fix bug\n",
        encoding="utf-8")
    response = make_client(tmp_path).get("/api/overview")
    assert response.status_code == 200
    body = response.json()
    assert len(body["repos"]) == 1
    repo = body["repos"][0]
    assert repo["mod"] == "CityMod"
    assert repo["open_count"] == 1
    assert repo["items"][0]["waits_for_author"] is True
    assert body["warnings"] == []


def test_overview_warns_for_known_mod_without_section(tmp_path: Path) -> None:
    make_mod_repo(tmp_path)
    (tmp_path / "tracking.md").write_text("## OtherMod\nupdated: 2026-11-08\n",
                                          encoding="utf-8")
    response = make_client(tmp_path).get("/api/overview")
    assert response.status_code == 200
    assert response.json()["warnings"] == ["CityMod: no section in tracking.md"]
