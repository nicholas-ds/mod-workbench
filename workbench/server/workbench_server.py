"""Compose the app, wire the background jobs and serve it with uvicorn."""

from __future__ import annotations

import asyncio
import sys
from collections.abc import AsyncIterator, Callable, Sequence
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from workbench.boards.alerts import NewBoardTracker, ToastNotifier, ToastSourceDetector
from workbench.core.watch import FileChangeWatcher
from workbench.server.alert_job import AlertJob
from workbench.server.background_job import BackgroundJob
from workbench.server.blocking_board_alerter import BlockingBoardAlerter
from workbench.server.root_env import RootEnv
from workbench.server.serve_settings import DEFAULT_ROOTS, HOST, ROOTS_ENV
from workbench.server.workbench_parts import WorkbenchParts


class WorkbenchServer:
    """Compose the app, wire the background jobs and serve it with uvicorn."""

    def run(self, port: int) -> None:
        uvicorn.run(self._app(), host=HOST, port=port, log_level="warning")

    def _app(self) -> FastAPI:
        roots = RootEnv(ROOTS_ENV, DEFAULT_ROOTS).read()
        parts = WorkbenchParts()
        app = parts.factory.create_app(roots)
        extra_jobs: Sequence[BackgroundJob] = getattr(app.state, "background_jobs", [])
        jobs: list[BackgroundJob] = [AlertJob(self._alerter(parts, roots)), *extra_jobs]
        app.router.lifespan_context = self._lifespan(jobs)
        return app

    def _lifespan(self, jobs: Sequence[BackgroundJob]) -> Callable[[FastAPI], AsyncIterator[None]]:
        @asynccontextmanager
        async def context(_app: FastAPI) -> AsyncIterator[None]:
            tasks = [asyncio.create_task(job.run()) for job in jobs]
            yield
            for task in tasks:
                task.cancel()
            for task in tasks:
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            for job in reversed(jobs):
                try:
                    await job.close()
                except Exception as error:  # noqa: BLE001 - a broken close must not stop the others
                    print(f"[Workbench] close failed: {type(job).__name__}: {error}",
                          file=sys.stderr)

        return context

    def _alerter(self, parts: WorkbenchParts, roots: list[Path]) -> BlockingBoardAlerter:
        return BlockingBoardAlerter(
            watcher=FileChangeWatcher(),
            registry=parts.registry(roots),
            roots=roots,
            tracker=NewBoardTracker(),
            notifier=ToastNotifier(ToastSourceDetector().detect()),
        )
