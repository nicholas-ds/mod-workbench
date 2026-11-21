"""Tests for SpecLoader and SpecValidator."""

from pathlib import Path

import pytest

from workbench.testspec import SpecError, SpecLoader, SpecValidator

REGISTERED_BASELINES = frozenset({"baseline-main"})
TEST_SLOT = "quicksave"

BASE = [
    "baseline: baseline-main",
    "goal: the mod menu opens",
]

STEPS = [
    "steps:",
    "  - action: launch the game",
    "    expect: the main menu shows",
]

VALID_SPEC = BASE + ["slot: quicksave"] + STEPS


def write_spec(tmp_path: Path, lines: list[str]) -> Path:
    path = tmp_path / "tests" / "spec-01.yaml"
    path.parent.mkdir(exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def load_and_validate(tmp_path: Path, lines: list[str]) -> None:
    spec = SpecLoader().load(write_spec(tmp_path, lines))
    SpecValidator().validate(spec, REGISTERED_BASELINES, TEST_SLOT)


def test_valid_spec_passes(tmp_path: Path) -> None:
    spec = SpecLoader().load(write_spec(tmp_path, VALID_SPEC))
    assert spec["baseline"] == "baseline-main"
    assert spec["steps"] == [
        {"action": "launch the game", "expect": "the main menu shows"}
    ]
    load_and_validate(tmp_path, VALID_SPEC)


def test_missing_baseline_field_rejected(tmp_path: Path) -> None:
    lines = ["goal: the mod menu opens"] + STEPS
    with pytest.raises(SpecError):
        load_and_validate(tmp_path, lines)


def test_unregistered_baseline_rejected(tmp_path: Path) -> None:
    lines = [line.replace("baseline-main", "unknown-save") for line in BASE]
    with pytest.raises(SpecError):
        load_and_validate(tmp_path, lines + STEPS)


def test_other_slot_rejected(tmp_path: Path) -> None:
    lines = BASE + ["slot: main-save"] + STEPS
    with pytest.raises(SpecError):
        load_and_validate(tmp_path, lines)


def test_step_without_expect_rejected(tmp_path: Path) -> None:
    lines = BASE + ["steps:", "  - action: launch the game"]
    with pytest.raises(SpecError):
        load_and_validate(tmp_path, lines)
