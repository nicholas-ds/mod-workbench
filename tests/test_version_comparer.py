"""Tests for the version comparer."""

from workbench.version_comparer import VersionComparer


def test_newer_patch_is_newer() -> None:
    assert VersionComparer().is_newer("1.19.4", "1.19.3") is True


def test_ten_is_newer_than_nine() -> None:
    assert VersionComparer().is_newer("1.19.10", "1.19.9") is True


def test_equal_is_not_newer() -> None:
    assert VersionComparer().is_newer("1.19.3", "1.19.3") is False


def test_older_is_not_newer() -> None:
    assert VersionComparer().is_newer("1.19.2", "1.19.3") is False


def test_missing_part_counts_as_zero() -> None:
    assert VersionComparer().is_newer("2.1.0", "2.1") is False


def test_empty_input_is_false() -> None:
    comparer = VersionComparer()
    assert comparer.is_newer("", "1.0") is False
    assert comparer.is_newer("1.0", "") is False


def test_suffix_text_is_ignored() -> None:
    assert VersionComparer().is_newer("1.2.4rc1", "1.2.3") is True
    assert VersionComparer().is_newer("1.2.3", "1.2.3rc1") is False
