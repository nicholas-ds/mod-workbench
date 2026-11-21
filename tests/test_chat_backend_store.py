"""Tests for ChatBackendStore."""

import json
from pathlib import Path

from workbench.chat_backend_store import ChatBackendStore


def test_load_missing_file_is_claude(tmp_path: Path) -> None:
    assert ChatBackendStore(tmp_path / "chat_backends.json").load("Workbench") == "claude"


def test_save_opencode_and_load(tmp_path: Path) -> None:
    path = tmp_path / "chat_backends.json"
    store = ChatBackendStore(path)
    store.save("Workbench", "opencode")
    assert store.load("Workbench") == "opencode"
    assert json.loads(path.read_text(encoding="utf-8")) == {"Workbench": "opencode"}
    assert ChatBackendStore(path).load("Workbench") == "opencode"


def test_save_claude_removes_entry(tmp_path: Path) -> None:
    path = tmp_path / "chat_backends.json"
    store = ChatBackendStore(path)
    store.save("Workbench", "opencode")
    store.save("Workbench", "claude")
    assert store.load("Workbench") == "claude"
    assert json.loads(path.read_text(encoding="utf-8")) == {}
    store.save("NewChat", "claude")
    assert json.loads(path.read_text(encoding="utf-8")) == {}


def test_save_non_opencode_key_is_stored(tmp_path: Path) -> None:
    path = tmp_path / "chat_backends.json"
    store = ChatBackendStore(path)
    store.save("Workbench", "mistral")
    assert store.load("Workbench") == "mistral"
    assert json.loads(path.read_text(encoding="utf-8")) == {"Workbench": "mistral"}
    assert ChatBackendStore(path).load("Workbench") == "mistral"


def test_empty_string_and_non_string_load_claude(tmp_path: Path) -> None:
    path = tmp_path / "chat_backends.json"
    path.write_text(json.dumps({"Workbench": "", "Other": 5}), encoding="utf-8")
    store = ChatBackendStore(path)
    assert store.load("Workbench") == "claude"
    assert store.load("Other") == "claude"


def test_corrupt_file_loads_claude_and_save_recovers(tmp_path: Path) -> None:
    path = tmp_path / "chat_backends.json"
    path.write_text("{not json", encoding="utf-8")
    store = ChatBackendStore(path)
    assert store.load("Workbench") == "claude"
    store.save("Workbench", "opencode")
    assert store.load("Workbench") == "opencode"


def test_disabled_store_none_path() -> None:
    store = ChatBackendStore(None)
    assert store.load("Workbench") == "claude"
    store.save("Workbench", "opencode")
    assert store.load("Workbench") == "claude"
