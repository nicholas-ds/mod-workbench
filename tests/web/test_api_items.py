"""Tests for serving board item files over HTTP."""

from pathlib import Path

from api_fixtures import LAYOUT_BOARD, make_client, make_mod_repo, write_board


def test_item_escape_is_404(tmp_path: Path) -> None:
    repo = make_mod_repo(tmp_path)
    folder = write_board(repo, "layout", LAYOUT_BOARD)
    (folder / "shot.png").write_bytes(b"png")
    (tmp_path / "secret.txt").write_text("top", encoding="utf-8")
    client = make_client(tmp_path)
    assert client.get(
        "/api/mods/CityMod/boards/layout/items/%2e%2e/secret.txt").status_code == 404
    assert client.get("/api/mods/CityMod/boards/layout/items/C:/x.png").status_code == 404


def test_html_item_has_sandbox_csp(tmp_path: Path) -> None:
    repo = make_mod_repo(tmp_path)
    folder = write_board(repo, "layout", LAYOUT_BOARD)
    (folder / "diagram.html").write_text("<p>hi</p>", encoding="utf-8")
    response = make_client(tmp_path).get(
        "/api/mods/CityMod/boards/layout/items/diagram.html")
    assert response.status_code == 200
    assert response.headers["content-security-policy"] == (
        "sandbox; default-src 'none'; style-src 'unsafe-inline'; img-src data:")


def test_item_is_revalidated_by_the_browser(tmp_path: Path) -> None:
    repo = make_mod_repo(tmp_path)
    folder = write_board(repo, "layout", LAYOUT_BOARD)
    (folder / "shot.png").write_bytes(b"png")
    response = make_client(tmp_path).get("/api/mods/CityMod/boards/layout/items/shot.png")
    assert response.headers["cache-control"] == "no-cache"


def test_html_item_gets_scrollbar_style(tmp_path: Path) -> None:
    repo = make_mod_repo(tmp_path)
    folder = write_board(repo, "layout", LAYOUT_BOARD)
    (folder / "diagram.html").write_text("<html><head><title>t</title></head><body>hi</body></html>", encoding="utf-8")
    response = make_client(tmp_path).get("/api/mods/CityMod/boards/layout/items/diagram.html")
    assert "::-webkit-scrollbar" in response.text
    assert "color-scheme" not in response.text
    assert response.text.index("<style>") < response.text.index("</head>")
    assert "<body>hi</body>" in response.text
