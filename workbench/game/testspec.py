"""Read and validate one test spec file for the game runner."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import yaml


class SpecError(Exception):
    """One test spec file is unreadable or names a wrong save, slot or step."""


class SpecLoader:
    """Read one test spec YAML file into a mapping."""

    def load(self, path: Path) -> dict:
        text = self._read_text(path)
        return self._parse_mapping(path, text)

    def _read_text(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except OSError as exc:
            raise SpecError(f"cannot read {path}: {exc}") from exc

    def _parse_mapping(self, path: Path, text: str) -> dict:
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise SpecError(f"{path} has bad YAML: {exc}") from exc
        if not isinstance(data, dict):
            raise SpecError(f"{path} is not a mapping")
        return data


class SpecValidator:
    """Reject a test spec that misses fields, or names a wrong baseline, slot or step."""

    def validate(
        self,
        spec: Mapping[str, object],
        registered_baselines: frozenset[str],
        test_slot: str,
    ) -> None:
        self._reject_missing_fields(spec)
        self._reject_unregistered_baseline(spec, registered_baselines)
        # A spec with no `slot` key runs on the test slot by default.
        self._reject_other_slot(spec, test_slot)
        self._reject_bad_steps(spec)

    def _reject_missing_fields(self, spec: Mapping[str, object]) -> None:
        required = ("baseline", "goal", "steps")
        missing = [field for field in required if field not in spec]
        if missing:
            raise SpecError(f"spec misses fields: {', '.join(missing)}")

    def _reject_unregistered_baseline(
        self, spec: Mapping[str, object], registered_baselines: frozenset[str]
    ) -> None:
        baseline = spec["baseline"]
        if not isinstance(baseline, str) or baseline not in registered_baselines:
            raise SpecError(f"baseline {baseline!r} is not a registered baseline")

    def _reject_other_slot(self, spec: Mapping[str, object], test_slot: str) -> None:
        slot = spec.get("slot", test_slot)
        if not isinstance(slot, str) or slot != test_slot:
            raise SpecError(f"slot {slot!r} is not the test slot {test_slot!r}")

    def _reject_bad_steps(self, spec: Mapping[str, object]) -> None:
        steps = spec["steps"]
        if not isinstance(steps, list):
            raise SpecError("steps must be a list")
        for index, step in enumerate(steps, start=1):
            self._reject_bad_step(index, step)

    def _reject_bad_step(self, index: int, step: object) -> None:
        if not isinstance(step, Mapping):
            raise SpecError(f"step {index} is not a mapping")
        missing = [field for field in ("action", "expect") if field not in step]
        if missing:
            raise SpecError(f"step {index} misses fields: {', '.join(missing)}")
