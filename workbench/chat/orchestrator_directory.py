"""List the orchestrator entries: the platform folder plus every usable mod."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from workbench.core.config import ModConfig
from workbench.mods.mod_registry import ModRegistry
from workbench.chat.thread_registry import ChatThread


@dataclass(frozen=True)
class OrchestratorEntry:
    name: str
    folder: str


class OrchestratorDirectory:
    """Build one entry for the platform folder and one per usable mod."""

    def __init__(self, registry: ModRegistry, platform_folder: Path) -> None:
        self._registry = registry
        self._platform_folder = platform_folder

    def entries(self) -> tuple[OrchestratorEntry, ...]:
        main = OrchestratorEntry(name="main", folder=self._platform_folder.as_posix())
        return (main,) + tuple(self._entry(cfg) for cfg in self._mod_configs())

    def folder_of(self, name: str) -> str:
        orchestrator, _thread_id = ChatThread.split_name(name)
        for entry in self.entries():
            if entry.name == orchestrator:
                return entry.folder
        return ""

    def _mod_configs(self) -> list[ModConfig]:
        return [cfg for cfg in self._registry.all() if isinstance(cfg, ModConfig)]

    def _entry(self, cfg: ModConfig) -> OrchestratorEntry:
        return OrchestratorEntry(name=cfg.name, folder=cfg.repo.as_posix())
