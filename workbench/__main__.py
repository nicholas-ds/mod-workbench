"""Run one workbench subcommand: serve, init or check."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from workbench.archive.archive_command import build_archive_command
from workbench.boards.board_builder import BoardBuilder
from workbench.boards.board_check import BoardValidator
from workbench.boards.board_repository import BoardRepository
from workbench.boards.front_matter import FrontMatterParser
from workbench.core.config import ConfigError, ModConfig, ModConfigLoader
from workbench.mods.mod_init import ModInitializer
from workbench.server.serve_settings import DEFAULT_PORT, DEFAULT_ROOTS, PORT_ENV, ROOTS_ENV


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
        from workbench.server.workbench_server import WorkbenchServer

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
