"""Tests: the server lifespan starts the background jobs and closes them on shutdown."""

from __future__ import annotations

import asyncio

import pytest
from fastapi import FastAPI

from workbench.server.background_job import BackgroundJob
from workbench.server.workbench_server import WorkbenchServer


class FakeJob(BackgroundJob):
    """A background job that records run, cancel and close calls."""

    def __init__(self, name: str, log: list[str], fail_close: bool = False) -> None:
        self._name = name
        self._log = log
        self._fail_close = fail_close
        self.run_started = False
        self.was_cancelled = False
        self.close_calls = 0

    async def run(self) -> None:
        self.run_started = True
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            self.was_cancelled = True
            raise

    async def close(self) -> None:
        self.close_calls += 1
        self._log.append(f"close:{self._name}")
        if self._fail_close:
            raise RuntimeError("boom")


def _app_with(jobs: list[BackgroundJob]) -> FastAPI:
    app = FastAPI()
    app.router.lifespan_context = WorkbenchServer()._lifespan(jobs)
    return app


def test_run_is_started_for_every_job() -> None:
    jobs = [FakeJob("a", []), FakeJob("b", [])]
    app = _app_with(jobs)

    async def drive() -> None:
        lifespan = app.router.lifespan_context
        async with lifespan(app):
            await asyncio.sleep(0)
            assert all(job.run_started for job in jobs)

    asyncio.run(drive())


def test_shutdown_cancels_tasks_and_closes_each_job_once() -> None:
    log: list[str] = []
    jobs = [FakeJob("a", log), FakeJob("b", log)]
    app = _app_with(jobs)

    async def drive() -> None:
        lifespan = app.router.lifespan_context
        async with lifespan(app):
            await asyncio.sleep(0)

    asyncio.run(drive())

    assert all(job.was_cancelled for job in jobs)
    assert all(job.close_calls == 1 for job in jobs)


def test_close_runs_in_reverse_start_order() -> None:
    log: list[str] = []
    app = _app_with([FakeJob("a", log), FakeJob("b", log)])

    async def drive() -> None:
        lifespan = app.router.lifespan_context
        async with lifespan(app):
            pass

    asyncio.run(drive())

    assert log == ["close:b", "close:a"]


def test_failing_close_does_not_stop_the_next_close(
    capsys: pytest.CaptureFixture[str],
) -> None:
    log: list[str] = []
    app = _app_with([FakeJob("a", log, fail_close=True), FakeJob("b", log)])

    async def drive() -> None:
        lifespan = app.router.lifespan_context
        async with lifespan(app):
            pass

    asyncio.run(drive())

    assert log == ["close:b", "close:a"]
    assert "[Workbench] close failed: FakeJob: boom" in capsys.readouterr().err
