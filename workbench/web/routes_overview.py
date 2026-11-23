"""`GET /api/overview`: tasks per mod from the master tracking file."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date
from pathlib import Path

from fastapi import APIRouter

from workbench.core.config import ModConfig
from workbench.mods.mod_registry import ModRegistry
from workbench.mods.task_overview import TaskOverviewReader


class OverviewRoutes:
    """`GET /api/overview`: tasks per mod from the master tracking file."""

    def __init__(self, registry: ModRegistry, reader: TaskOverviewReader,
                 master_path: Path) -> None:
        self._registry, self._reader, self._master_path = registry, reader, master_path
        self.routes = APIRouter()
        self.routes.add_api_route("/api/overview", self.overview, methods=["GET"])

    def overview(self) -> dict[str, object]:
        overview = self._reader.read(self._master_path, date.today(), self._known_mods())
        return asdict(overview)

    def _known_mods(self) -> tuple[str, ...]:
        return tuple(result.name for result in self._registry.all()
                     if isinstance(result, ModConfig))
