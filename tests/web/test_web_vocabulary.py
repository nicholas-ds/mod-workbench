"""Tests: the web page hardcodes no vocabulary, no hex colors, and serves at the root."""

import re
from pathlib import Path

from fastapi.testclient import TestClient

from workbench.server.workbench_parts import WorkbenchParts
from tests.support.api_fixtures import SILENT_PANE_SENDER

WEB_DIR = Path(__file__).resolve().parents[2] / "web"
FORBIDDEN = ("Naming", "Game design", "CityBuilder", "Starfield")
HEX_COLOR = re.compile(r"#[0-9a-fA-F]{6}\b")


def _web_files() -> list[Path]:
    if not WEB_DIR.is_dir():
        return []
    return sorted(path for path in WEB_DIR.iterdir() if path.is_file())


def test_no_hex_outside_tokens() -> None:
    files = [path for path in _web_files() if path.name != "tokens.css"]
    assert files, "web/ has no files to check"
    for path in files:
        found = HEX_COLOR.findall(path.read_text(encoding="utf-8"))
        assert not found, f"{path.name} has hex colors: {found}"


def test_no_domain_vocabulary() -> None:
    files = _web_files()
    assert files, "web/ has no files"
    for path in files:
        text = path.read_text(encoding="utf-8")
        for word in FORBIDDEN:
            assert word not in text, f"{path.name} hardcodes {word}"


def test_html_items_never_get_allow_same_origin() -> None:
    text = (WEB_DIR / "item_renderers.js").read_text(encoding="utf-8")
    assert "sandbox" in text
    assert "allow-same-origin" not in text
    assert "allow-scripts" not in text


KEY_LITERALS = ('"1"', '"2"', '"3"', '"Enter"', '"s"')


def test_keys_are_1_2_3_enter_s() -> None:
    text = (WEB_DIR / "key_map.js").read_text(encoding="utf-8")
    for key in KEY_LITERALS:
        assert key in text, f"key_map.js does not map {key}"


def test_index_served_at_root(tmp_path: Path) -> None:
    client = TestClient(WorkbenchParts(SILENT_PANE_SENDER).factory.create_app([tmp_path]),
                        base_url="http://127.0.0.1")
    response = client.get("/")
    assert response.status_code == 200
    assert "<table" in response.text or 'id="app"' in response.text
