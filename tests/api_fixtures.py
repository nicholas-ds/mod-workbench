"""Shared fixtures for the board API tests: a mod repo, board texts, a client."""

from pathlib import Path

from fastapi.testclient import TestClient

from workbench.__main__ import WorkbenchParts

MOD_TOML = """\
name = "CityMod"
platform = "."
screens = ["ui/**/*.swf"]
boards = "boards"
status = "status.toml"
tracking = "tracking.md"
log = "LOG.md"
briefs = "briefs"
exports = "exports"
"""

STATUS_TOML = """\
phase = "build"

[workers.planner]
pane = "plan"
"""

LAYOUT_BOARD = """\
---
title: Queue layout
raised_by: build
created: "2026-11-07T10:00:00"
tags: [ui]
items:
  - file: shot.png
    caption: Current queue
  - file: diagram.html
    caption: Draft diagram
questions:
  - id: layout
    type: choice
    prompt: Which queue layout?
    options:
      - id: compact
        label: Compact
      - id: wide
        label: Wide
    default: compact
    blocking: true
    affects: [queue/swf]
---
Body.
"""

COLOR_BOARD = """\
---
title: Tag color
raised_by: research
created: "2026-11-08T09:00:00"
tags: [ui]
questions:
  - id: color
    type: choice
    prompt: Which tag color?
    options:
      - id: gray
        label: Gray
      - id: blue
        label: Blue
    default: gray
    blocking: false
    affects: [ui/naming, hud/tags, bar/sort]
---
Body.
"""

BAD_BOARD = "---\nprompt: no title here\n---\n"

ANSWERS_URL = "/api/mods/CityMod/boards/layout/answers"


def make_mod_repo(root: Path) -> Path:
    repo = root / "CityMod"
    (repo / "boards" / "open").mkdir(parents=True)
    (repo / "workbench.toml").write_text(MOD_TOML, encoding="utf-8")
    (repo / "status.toml").write_text(STATUS_TOML, encoding="utf-8")
    return repo


def write_board(repo: Path, board_id: str, text: str) -> Path:
    folder = repo / "boards" / "open" / board_id
    folder.mkdir(parents=True)
    (folder / "board.md").write_text(text, encoding="utf-8")
    return folder


def make_client(root: Path) -> TestClient:
    return TestClient(WorkbenchParts().factory.create_app([root]),
                      base_url="http://127.0.0.1")
