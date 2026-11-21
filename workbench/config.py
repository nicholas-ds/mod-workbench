"""Load the thin `workbench.toml` config of one mod repo."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

CONFIG_FILENAME = "workbench.toml"
_PATH_FIELDS = ("platform", "boards", "status", "tracking", "log", "briefs", "exports")
_REQUIRED_FIELDS = ("name", "screens") + _PATH_FIELDS


class ConfigError(Exception):
    """A mod repo has no usable `workbench.toml`."""


@dataclass(frozen=True)
class ModConfig:
    name: str
    repo: Path
    platform: Path
    screens: tuple[str, ...]
    boards: Path
    status: Path
    tracking: Path
    log: Path
    briefs: Path
    exports: Path


@dataclass(frozen=True)
class ModError:
    repo: Path
    reason: str


class ModConfigLoader:
    """Read `workbench.toml` of one mod repo into a `ModConfig`."""

    def load(self, repo: Path) -> ModConfig:
        resolved_repo = repo.resolve()
        config_path = resolved_repo / CONFIG_FILENAME
        raw = self._read_toml(config_path)
        self._reject_missing_fields(raw, config_path)
        screens = self._screens(raw, config_path)
        name = self._name(raw, config_path)
        return self._build_config(raw, resolved_repo, name, screens)

    def _read_toml(self, config_path: Path) -> dict[str, object]:
        if not config_path.is_file():
            raise ConfigError(f"no {CONFIG_FILENAME} in {config_path.parent}")
        try:
            return tomllib.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
            raise ConfigError(f"cannot read {config_path}: {exc}") from exc

    def _reject_missing_fields(self, raw: dict[str, object], config_path: Path) -> None:
        missing = [field for field in _REQUIRED_FIELDS if field not in raw]
        if missing:
            raise ConfigError(f"{config_path} misses fields: {', '.join(missing)}")

    def _screens(self, raw: dict[str, object], config_path: Path) -> tuple[str, ...]:
        screens = raw["screens"]
        if not isinstance(screens, list) or not all(isinstance(s, str) for s in screens):
            raise ConfigError(f"{config_path}: screens must be a list of strings")
        return tuple(screens)

    def _name(self, raw: dict[str, object], config_path: Path) -> str:
        if not isinstance(raw["name"], str):
            raise ConfigError(f"{config_path}: name must be a string")
        return raw["name"]

    def _build_config(
        self,
        raw: dict[str, object],
        repo: Path,
        name: str,
        screens: tuple[str, ...],
    ) -> ModConfig:
        paths = {field: (repo / str(raw[field])).resolve() for field in _PATH_FIELDS}
        return ModConfig(
            name=name,
            repo=repo,
            platform=paths["platform"],
            screens=screens,
            boards=paths["boards"],
            status=paths["status"],
            tracking=paths["tracking"],
            log=paths["log"],
            briefs=paths["briefs"],
            exports=paths["exports"],
        )


class ModDiscovery:
    """Scan roots for mod repos, one result per repo, never raise."""

    def __init__(self, loader: ModConfigLoader) -> None:
        self._loader = loader

    def discover(self, roots: list[Path]) -> list[ModConfig | ModError]:
        results: list[ModConfig | ModError] = []
        for root in roots:
            results.extend(self._root_results(root))
        return results

    def _root_results(self, root: Path) -> list[ModConfig | ModError]:
        if not root.is_dir():
            return []
        return [
            self._child_result(child)
            for child in sorted(root.iterdir())
            if (child / CONFIG_FILENAME).is_file()
        ]

    def _child_result(self, repo: Path) -> ModConfig | ModError:
        try:
            return self._loader.load(repo)
        except ConfigError as exc:
            return ModError(repo=repo.resolve(), reason=str(exc))
