"""Run one workbench subcommand: serve, init or check."""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from workbench.boards.alerts import NewBoardTracker, ToastNotifier, ToastSourceDetector
from workbench.archive.archive_command import build_archive_command
from workbench.boards.answer_store import AnswerStore
from workbench.web.api import ApiFactory
from workbench.boards.board_builder import BoardBuilder
from workbench.boards.board_check import BoardValidator
from workbench.boards.board_lifecycle import BoardLifecycle
from workbench.boards.board_repository import OPEN_STATE, BoardRepository
from workbench.boards.board_types import BoardEntry
from workbench.core.config import ConfigError, ModConfig, ModConfigLoader, ModDiscovery
from workbench.boards.front_matter import FrontMatterParser
from workbench.boards.item_files import ItemKindDetector, SafeItemResolver
from workbench.mods.mod_init import ModInitializer
from workbench.mods.mod_registry import ModRegistry
from workbench.boards.note_writer import NoteWriter
from workbench.boards.queue import QueueSorter
from workbench.boards.rework import LogAppender, ReworkBriefWriter
from workbench.mods.status import StatusReader, WorkerExtractor
from workbench.core.tables import TableBuilder
from workbench.core.watch import FileChangeWatcher

ROOTS_ENV = "WORKBENCH_ROOTS"
DEFAULT_ROOTS = str(Path(__file__).resolve().parents[2])
HOST = "127.0.0.1"
PORT_ENV = "WORKBENCH_PORT"
DEFAULT_PORT = 8760


class BadPortError(ValueError):
    """The requested port is not an integer from 1 to 65535."""


class PortChooser:
    """Pick the serve port from the flag, then the env var, then the default."""

    def __init__(self, default: int) -> None:
        self._default = default

    def choose(self, argv_port: str | None, env_port: str | None) -> int:
        requested = argv_port if argv_port is not None else env_port
        if requested is None:
            return self._default
        return self._validated(requested)

    def _validated(self, raw: str) -> int:
        try:
            port = int(raw)
        except ValueError:
            raise BadPortError(f"port must be an integer, got {raw!r}") from None
        if not 1 <= port <= 65535:
            raise BadPortError(f"port must be between 1 and 65535, got {port}")
        return port


class RootEnv:
    """Read the mod root folders from one environment variable."""

    def __init__(self, name: str, default: str) -> None:
        self._name = name
        self._default = default

    def read(self) -> list[Path]:
        raw = os.environ.get(self._name, self._default)
        return [Path(part) for part in raw.split(os.pathsep) if part.strip()]


class WorkbenchParts:
    """Compose the default workbench parts."""

    def __init__(self) -> None:
        self.repository = BoardRepository(FrontMatterParser(), BoardBuilder())
        self.answers = AnswerStore()
        self.factory = ApiFactory(
            discovery=ModDiscovery(ModConfigLoader()),
            boards=self.repository,
            answers=self.answers,
            lifecycle=BoardLifecycle(),
            sorter=QueueSorter(),
            table_builder=TableBuilder(),
            rework_writer=ReworkBriefWriter(LogAppender()),
            note_writer=NoteWriter(),
            status_reader=StatusReader(),
            worker_extractor=WorkerExtractor(),
            resolver=SafeItemResolver(),
            kinds=ItemKindDetector(),
            watcher=FileChangeWatcher(),
        )

    def registry(self, roots: list[Path]) -> ModRegistry:
        return ModRegistry(ModDiscovery(ModConfigLoader()), roots,
                           self.repository, self.answers)


class BlockingBoardAlerter:
    """Watch the roots and toast once for each new blocking board."""

    def __init__(self, watcher: FileChangeWatcher, registry: ModRegistry,
                 roots: list[Path], tracker: NewBoardTracker,
                 notifier: ToastNotifier) -> None:
        self._watcher, self._registry = watcher, registry
        self._roots, self._tracker, self._notifier = roots, tracker, notifier

    async def run(self) -> None:
        async for _batch in self._watcher.changes(self._roots):
            self._alert_fresh()

    def _alert_fresh(self) -> None:
        for entry in self._tracker.new_blocking(self._open_entries()):
            self._notifier.notify("Blocking board", entry.board.title)

    def _open_entries(self) -> list[BoardEntry]:
        return [entry for cfg in self._mods() for entry in self._entries_of(cfg)]

    def _mods(self) -> list[ModConfig]:
        return [result for result in self._registry.all() if isinstance(result, ModConfig)]

    def _entries_of(self, cfg: ModConfig) -> list[BoardEntry]:
        listed = self._registry.entries(cfg, OPEN_STATE)
        return [entry for entry in listed if isinstance(entry, BoardEntry)]


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


class WorkbenchCommands:
    """Parse argv and run one subcommand: serve (default), init, check or archive."""

    def run(self, argv: list[str]) -> int:
        args = self._parse(argv)
        commands = {"init": self._run_init, "check": self._run_check, "archive": self._run_archive}
        return commands.get(args.command, self._run_serve)(args)

    def _run_archive(self, args: argparse.Namespace) -> int:
        roots = RootEnv(ROOTS_ENV, DEFAULT_ROOTS).read()
        print(build_archive_command().run(roots, args.days, args.apply))
        return 0

    def _parse(self, argv: list[str]) -> argparse.Namespace:
        parser = argparse.ArgumentParser(prog="python -m workbench",
                                         description="Local platform on top of mod repos.")
        sub = parser.add_subparsers(dest="command")
        serve = sub.add_parser("serve", help="serve the workbench web UI on localhost")
        serve.add_argument("--port", default=None,
                           help="TCP port to listen on (default: WORKBENCH_PORT or 8760)")
        init = sub.add_parser("init", help="write workbench.toml and folders for one mod repo")
        init.add_argument("repo", type=Path, help="folder of the mod repo")
        init.add_argument("--name", required=True, help="display name of the mod")
        init.add_argument("--platform", type=Path, default=None,
                          help="path of the workbench platform (default: repo parent)")
        check = sub.add_parser("check", help="check one board folder for problems")
        check.add_argument("folder", type=Path, help="folder holding board.md")
        archive = sub.add_parser("archive", help="zip old done boards losslessly")
        archive.add_argument("--apply", action="store_true", help="write changes")
        archive.add_argument("--days", type=int, default=30, help="min board age")
        parser.set_defaults(port=None)
        return parser.parse_args(argv)

    def _run_serve(self, args: argparse.Namespace) -> int:
        env_port = os.environ.get(PORT_ENV)
        try:
            port = PortChooser(DEFAULT_PORT).choose(args.port, env_port)
        except BadPortError as error:
            print(str(error))
            return 2
        WorkbenchServer().run(port)
        return 0

    def _run_init(self, args: argparse.Namespace) -> int:
        repo = args.repo.resolve()
        platform = args.platform if args.platform is not None else repo.parent
        created = ModInitializer().init(repo, args.name, Path(platform).resolve())
        for path in created:
            print(f"created {path}")
        return 0

    def _run_check(self, args: argparse.Namespace) -> int:
        problems = self._validator(args.folder).check(args.folder)
        for line in problems:
            print(line)
        return 1 if problems else 0

    def _validator(self, folder: Path) -> BoardValidator:
        repository = BoardRepository(FrontMatterParser(), BoardBuilder())
        config = self._mod_config(folder)
        status_dir = config.status if config is not None else None
        mod_name = config.name if config is not None else None
        return BoardValidator(repository, status_dir, mod_name)

    def _mod_config(self, folder: Path) -> ModConfig | None:
        repo_root = folder.resolve().parents[2]
        try:
            return ModConfigLoader().load(repo_root)
        except ConfigError:
            return None


def main() -> None:
    raise SystemExit(WorkbenchCommands().run(sys.argv[1:]))


if __name__ == "__main__":
    main()
