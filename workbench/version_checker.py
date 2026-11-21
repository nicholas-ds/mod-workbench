"""Build version reports for the tools the workbench depends on."""

from __future__ import annotations

from workbench.installed_version_reader import InstalledVersionReader
from workbench.latest_version_fetcher import LatestVersionFetcher
from workbench.version_comparer import VersionComparer
from workbench.version_report import VersionReport

_NOT_INSTALLED = "not installed"
_NO_LATEST = "could not read the latest version"


class VersionChecker:
    """Compare installed tool versions with their latest known versions."""

    def __init__(
        self,
        reader: InstalledVersionReader,
        fetcher: LatestVersionFetcher,
        comparer: VersionComparer,
    ) -> None:
        self._reader = reader
        self._fetcher = fetcher
        self._comparer = comparer

    def check(self) -> tuple[VersionReport, ...]:
        return (
            self._report(
                "claude-agent-sdk",
                self._reader.package("claude-agent-sdk"),
                self._fetcher.pypi("claude-agent-sdk"),
            ),
            self._report(
                "claude-code",
                self._reader.command(("claude", "--version")),
                self._fetcher.npm("@anthropic-ai/claude-code"),
            ),
            self._report(
                "opencode",
                self._reader.command(("opencode", "--version")),
                self._fetcher.npm("@opencode/cli"),
            ),
        )

    def _report(self, name: str, installed: str, latest: str) -> VersionReport:
        return VersionReport(
            name=name,
            installed=installed,
            latest=latest,
            update_available=self._comparer.is_newer(latest, installed),
            note=self._note(installed, latest),
        )

    def _note(self, installed: str, latest: str) -> str:
        if installed == "":
            return _NOT_INSTALLED
        if latest == "":
            return _NO_LATEST
        return ""
