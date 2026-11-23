"""`GET /api/mods/{name}/detail`: tails and folder names of one mod."""

from __future__ import annotations

from fastapi import APIRouter

from workbench.mods.mod_detail import ModDetail, ModDetailReader
from workbench.mods.mod_registry import ModRegistry


class DetailRoutes:
    """`GET /api/mods/{name}/detail`: tails and folder names of one mod."""

    def __init__(self, registry: ModRegistry, reader: ModDetailReader) -> None:
        self._registry, self._reader = registry, reader
        self.routes = APIRouter()
        self.routes.add_api_route("/api/mods/{name}/detail", self.detail, methods=["GET"])

    def detail(self, name: str) -> ModDetail:
        return self._reader.read(self._registry.require(name))
