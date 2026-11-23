"""Tests: the serve settings constants and the default roots folder."""

from pathlib import Path

import workbench

from workbench.server.serve_settings import DEFAULT_ROOTS


def test_default_roots_is_the_mods_folder() -> None:
    assert Path(DEFAULT_ROOTS) == Path(workbench.__file__).resolve().parents[2]
