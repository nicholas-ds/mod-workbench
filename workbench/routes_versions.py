"""HTTP routes for version reports: cached GET and forced refresh POST."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter

from workbench.version_cache import VersionCache
from workbench.version_checker import VersionChecker
from workbench.version_report import VersionReport


class VersionRoutes:
    """GET cached version reports, POST a forced refresh."""

    def __init__(self, checker: VersionChecker, cache: VersionCache) -> None:
        self._checker = checker
        self._cache = cache
        self.routes = APIRouter()
        self.routes.add_api_route("/api/versions", self.versions, methods=["GET"])
        self.routes.add_api_route("/api/versions/refresh", self.refresh, methods=["POST"])

    def versions(self) -> dict[str, list[dict[str, object]]]:
        reports = self._cache.load()
        if reports is None:
            reports = self._check_and_save()
        return self._payload(reports)

    def refresh(self) -> dict[str, list[dict[str, object]]]:
        return self._payload(self._check_and_save())

    def _check_and_save(self) -> tuple[VersionReport, ...]:
        reports = self._checker.check()
        self._cache.save(reports)
        return reports

    def _payload(self, reports: tuple[VersionReport, ...]) -> dict[str, list[dict[str, object]]]:
        return {"versions": [asdict(report) for report in reports]}
