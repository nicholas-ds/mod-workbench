"""`GET /api/mods`: one row per mod with open boards, per-workspace status and workers."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter

from workbench.core.config import ModConfig, ModError
from workbench.mods.mod_registry import ModRegistry
from workbench.mods.status import Status, StatusReader, WorkerExtractor
from workbench.agents.worker_scanner import BusyWorkerCounter, WorkerCounts


@dataclass(frozen=True)
class ModRow:
    record: dict[str, object]
    workers: list[dict[str, object]]


class ModsRoutes:
    """`GET /api/mods`: one row per mod with open boards, per-workspace status and workers."""

    def __init__(self, registry: ModRegistry, status_reader: StatusReader,
                 worker_extractor: WorkerExtractor,
                 worker_counter: BusyWorkerCounter) -> None:
        self._registry, self._status_reader = registry, status_reader
        self._worker_extractor, self._worker_counter = worker_extractor, worker_counter
        self.routes = APIRouter()
        self.routes.add_api_route("/api/mods", self.mods, methods=["GET"])

    def mods(self) -> dict[str, object]:
        results = self._registry.all()
        counts = self._worker_counter.count_by_repo(
            [str(result.repo) for result in results if not isinstance(result, ModError)])
        mod_rows = [self._row(result, counts) for result in results]
        workers = [worker for row in mod_rows for worker in row.workers]
        return {"rows": [row.record for row in mod_rows], "workers": workers}

    def _row(self, result: ModConfig | ModError,
             counts: dict[str, WorkerCounts]) -> ModRow:
        if isinstance(result, ModError):
            return ModRow({"repo": str(result.repo), "error": result.reason}, [])
        return ModRow(self._mod_record(result, counts), self._workers_of(result))

    def _mod_record(self, cfg: ModConfig,
                    counts: dict[str, WorkerCounts]) -> dict[str, object]:
        repo_counts = counts.get(str(cfg.repo), WorkerCounts())
        return {"name": cfg.name, "repo": str(cfg.repo),
                "open_boards": self._registry.open_count(cfg),
                "status": self._workspace_rows(cfg),
                "agents": repo_counts.active,
                "stalled_agents": repo_counts.stalled}

    def _workspace_rows(self, cfg: ModConfig) -> list[dict[str, object]]:
        return [{"workspace": workspace.workspace, "values": dict(workspace.values)}
                for workspace in self._status_reader.read_all(cfg.status)]

    def _workers_of(self, cfg: ModConfig) -> list[dict[str, object]]:
        workers: list[dict[str, object]] = []
        for workspace in self._status_reader.read_all(cfg.status):
            status = Status(values=workspace.values)
            workers.extend({"mod": cfg.name, "workspace": workspace.workspace,
                            "name": worker.name, "fields": dict(worker.fields)}
                           for worker in self._worker_extractor.extract(status))
        return workers
