"""Tests: static web responses carry Cache-Control no-cache, API responses do not."""

from __future__ import annotations

from pathlib import Path

from api_fixtures import make_client


def test_static_file_has_no_cache_header(tmp_path: Path) -> None:
    response = make_client(tmp_path).get("/clay.css")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-cache"


def test_index_has_no_cache_header(tmp_path: Path) -> None:
    response = make_client(tmp_path).get("/")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-cache"


def test_api_route_is_not_touched(tmp_path: Path) -> None:
    response = make_client(tmp_path).get("/api/mods")
    assert response.status_code == 200
    assert "cache-control" not in response.headers
