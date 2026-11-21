"""List every registered workspace pane the author can message."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from workbench.config import ModConfig
from workbench.mod_registry import ModRegistry
from workbench.pane_registry import OrchestratorPane, PaneRegistry

ORCHESTRATOR_NAME = "main-orchestrator"
_ORCHESTRATOR_FILE = Path("status") / "main-orchestrator.toml"


@dataclass(frozen=True)
class PaneEntry:
    """One registered pane and the repo that holds its messages."""

    name: str
    mod: str | None
    repo: Path
    pane: OrchestratorPane
    status_file: Path


class PaneDirectory:
    """List the targetable panes: the orchestrator and each mod's status panes."""

    def __init__(self, registry: ModRegistry, workbench_root: Path) -> None:
        self._registry, self._workbench_root = registry, workbench_root

    def list_all(self) -> tuple[PaneEntry, ...]:
        mod_entries = self._mod_entries()
        shared = {entry.pane.surface for entry in mod_entries}
        orchestrators = tuple(entry for entry in self._orchestrator_entries()
                              if entry.pane.surface not in shared)
        return orchestrators + mod_entries

    def find(self, name: str) -> PaneEntry | None:
        for entry in self.list_all():
            if entry.name == name:
                return entry
        return None

    def _orchestrator_entries(self) -> tuple[PaneEntry, ...]:
        pane = PaneRegistry(self._workbench_root / _ORCHESTRATOR_FILE).find()
        if pane is None:
            return ()
        return (PaneEntry(name=ORCHESTRATOR_NAME, mod=None,
                          repo=self._workbench_root, pane=pane,
                          status_file=self._workbench_root / _ORCHESTRATOR_FILE),)

    def _mod_entries(self) -> tuple[PaneEntry, ...]:
        configs = [item for item in self._registry.all() if isinstance(item, ModConfig)]
        return tuple(entry for cfg in configs for entry in self._mod_entries_in(cfg))

    def _mod_entries_in(self, cfg: ModConfig) -> tuple[PaneEntry, ...]:
        if not cfg.status.is_dir():
            return ()
        found = (self._pane_entry(cfg, path)
                 for path in sorted(cfg.status.glob("*.toml")))
        return tuple(entry for entry in found if entry is not None)

    @staticmethod
    def _pane_entry(cfg: ModConfig, path: Path) -> PaneEntry | None:
        pane = PaneRegistry(path).find()
        if pane is None:
            return None
        return PaneEntry(name=path.stem, mod=cfg.name, repo=cfg.repo, pane=pane,
                         status_file=path)
