"""Tests for the OpenCode server process edge (no real opencode runs)."""

import json
import os
import sys
from pathlib import Path

from workbench.opencode.opencode_server_process import OpencodeServerProcess, parse_listen_url


def write_state(path: Path, pid: int, url: str, password: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"url": url, "pid": pid, "password": password}), encoding="utf-8"
    )


def test_reuse_returns_url_and_password_from_state_file(
    tmp_path: Path, monkeypatch
) -> None:
    state_path = tmp_path / "status" / "opencode_server.json"
    write_state(state_path, os.getpid(), "http://127.0.0.1:40999", "pw123")
    monkeypatch.setattr(
        OpencodeServerProcess, "_url_answers", lambda self, url, password: True
    )
    process = OpencodeServerProcess(state_path, exe="opencode-must-not-run")
    assert process.ensure(tmp_path) == ("http://127.0.0.1:40999", "pw123")


def test_dead_pid_starts_a_new_server(tmp_path: Path, monkeypatch) -> None:
    state_path = tmp_path / "opencode_server.json"
    write_state(state_path, 999_999_999, "http://127.0.0.1:40999", "pw123")
    monkeypatch.setattr(
        OpencodeServerProcess,
        "_start",
        lambda self, cwd: ("http://127.0.0.1:42222", "fresh"),
    )
    process = OpencodeServerProcess(state_path, exe="opencode-must-not-run")
    assert process.ensure(tmp_path) == ("http://127.0.0.1:42222", "fresh")


def test_stop_kills_pid_and_deletes_state(tmp_path: Path, monkeypatch) -> None:
    state_path = tmp_path / "opencode_server.json"
    write_state(state_path, os.getpid(), "http://127.0.0.1:40999", "pw123")
    killed: list[int] = []
    monkeypatch.setattr(
        OpencodeServerProcess, "_kill", lambda self, pid: killed.append(pid)
    )
    OpencodeServerProcess(state_path).stop()
    assert killed == [os.getpid()]
    assert not state_path.exists()


def test_parse_listen_url_variants() -> None:
    wrapped = "opencode serve listening on (http://127.0.0.1:41111)\n"
    bare = "opencode listening on http://127.0.0.1:41112 ready"
    assert parse_listen_url(wrapped) == "http://127.0.0.1:41111"
    assert parse_listen_url(bare) == "http://127.0.0.1:41112"
    assert parse_listen_url("no marker here") is None


def test_start_truncates_stale_log_url(tmp_path: Path) -> None:
    state_path = tmp_path / "status" / "opencode_server.json"
    log_path = state_path.parent / "opencode_server.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("server listening on http://127.0.0.1:1111\n", encoding="utf-8")
    if sys.platform == "win32":
        fake = state_path.parent / "fake-opencode.cmd"
        fake.write_text(
            "@echo server listening on http://127.0.0.1:2222\r\n", encoding="utf-8"
        )
    else:
        fake = state_path.parent / "fake-opencode.sh"
        fake.write_text(
            "#!/bin/sh\necho server listening on http://127.0.0.1:2222\n",
            encoding="utf-8",
        )
        fake.chmod(0o755)
    process = OpencodeServerProcess(state_path, exe=str(fake))
    url, _password = process.ensure(tmp_path)
    assert url == "http://127.0.0.1:2222"
    text = log_path.read_text(encoding="utf-8")
    assert "1111" not in text
    assert text.count("listening on") == 1
