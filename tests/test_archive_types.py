"""Tests for archive types and policy (board archive step 1, revision 1)."""

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from workbench.archive_policy import ArchivePolicy
from workbench.archive_types import ArchiveCandidate, BoardArchiveResult


def test_archive_candidate_has_only_board_dir() -> None:
    candidate = ArchiveCandidate(board_dir=Path("done/b1"))
    assert candidate.board_dir == Path("done/b1")


def test_archive_candidate_is_frozen() -> None:
    candidate = ArchiveCandidate(board_dir=Path("done/b1"))
    with pytest.raises(FrozenInstanceError):
        candidate.board_dir = Path("other")


def test_board_archive_result_fields() -> None:
    result = BoardArchiveResult(
        board_dir=Path("done/b1"),
        file_count=3,
        total_bytes=900,
        archived=True,
    )
    assert result.board_dir == Path("done/b1")
    assert result.file_count == 3
    assert result.total_bytes == 900
    assert result.archived is True
    assert result.error == ""


def test_board_archive_result_error() -> None:
    result = BoardArchiveResult(
        board_dir=Path("done/b2"),
        file_count=0,
        total_bytes=0,
        archived=False,
        error="zip check failed",
    )
    assert result.archived is False
    assert result.error == "zip check failed"


def test_board_archive_result_is_frozen() -> None:
    result = BoardArchiveResult(
        board_dir=Path("done/b1"), file_count=1, total_bytes=1, archived=False
    )
    with pytest.raises(FrozenInstanceError):
        result.file_count = 2


def test_archive_policy_defaults() -> None:
    policy = ArchivePolicy()
    assert policy.min_age_days == 30
