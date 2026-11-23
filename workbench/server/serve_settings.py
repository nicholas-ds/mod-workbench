"""Serve settings: env var names, default roots folder, host and port."""

from pathlib import Path

ROOTS_ENV = "WORKBENCH_ROOTS"
DEFAULT_ROOTS = str(Path(__file__).resolve().parents[3])
HOST = "127.0.0.1"
PORT_ENV = "WORKBENCH_PORT"
DEFAULT_PORT = 8760
