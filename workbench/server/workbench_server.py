"""Compose the app, wire the alert loop and serve it with uvicorn."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from workbench.boards.alerts import NewBoardTracker, ToastNotifier, ToastSourceDetector
from workbench.core.watch import FileChangeWatcher
from workbench.server.blocking_board_alerter import BlockingBoardAlerter
from workbench.server.root_env import RootEnv
from workbench.server.serve_settings import DEFAULT_ROOTS, HOST, ROOTS_ENV
from workbench.server.workbench_parts import WorkbenchParts


class WorkbenchServer:
    """Compose the app, wire the alert loop and serve it with uvicorn."""

    def __init__(self) -> None:
        self._alert_task: asyncio.Task[None] | None = None

    def run(self, port: int) -> None:
        uvicorn.run(self._app(), host=HOST, port=port, log_level="warning")

    def _app(self) -> FastAPI:
        roots = RootEnv(ROOTS_ENV, DEFAULT_ROOTS).read()
        parts = WorkbenchParts()
        app = parts.factory.create_app(roots)
        app.router.lifespan_context = self._lifespan(self._alerter(parts, roots))
        return app

    def _lifespan(self, alerter: BlockingBoardAlerter) -> Callable[[FastAPI], AsyncIterator[None]]:
        @asynccontextmanager
        async def context(_app: FastAPI) -> AsyncIterator[None]:
            self._alert_task = asyncio.create_task(alerter.run())
            yield
            if self._alert_task is not None:
                self._alert_task.cancel()

        return context

    def _alerter(self, parts: WorkbenchParts, roots: list[Path]) -> BlockingBoardAlerter:
        return BlockingBoardAlerter(
            watcher=FileChangeWatcher(),
            registry=parts.registry(roots),
            roots=roots,
            tracker=NewBoardTracker(),
            notifier=ToastNotifier(ToastSourceDetector().detect()),
        )
