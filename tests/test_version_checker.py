"""Tests for the version checker."""

from workbench.version_checker import VersionChecker
from workbench.version_comparer import VersionComparer


class FakeReader:
    def __init__(
        self,
        packages: dict[str, str],
        commands: dict[tuple[str, ...], str],
    ) -> None:
        self._packages = packages
        self._commands = commands

    def package(self, name: str) -> str:
        return self._packages.get(name, "")

    def command(self, args: tuple[str, ...]) -> str:
        return self._commands.get(args, "")


class FakeFetcher:
    def __init__(self, pypi: dict[str, str], npm: dict[str, str]) -> None:
        self._pypi = pypi
        self._npm = npm

    def pypi(self, package: str) -> str:
        return self._pypi.get(package, "")

    def npm(self, package: str) -> str:
        return self._npm.get(package, "")


def make_checker(
    packages: dict[str, str],
    commands: dict[tuple[str, ...], str],
    pypi: dict[str, str],
    npm: dict[str, str],
) -> VersionChecker:
    return VersionChecker(
        FakeReader(packages, commands),
        FakeFetcher(pypi, npm),
        VersionComparer(),
    )


def installed_everywhere(version: str) -> tuple[
    dict[str, str],
    dict[tuple[str, ...], str],
]:
    return (
        {"claude-agent-sdk": version},
        {
            ("claude", "--version"): version,
            ("opencode", "--version"): version,
        },
    )


def latest_everywhere(version: str) -> tuple[dict[str, str], dict[str, str]]:
    return (
        {"claude-agent-sdk": version},
        {"@anthropic-ai/claude-code": version, "@opencode/cli": version},
    )


def test_update_available_when_latest_is_newer() -> None:
    packages, commands = installed_everywhere("1.0.0")
    pypi, npm = latest_everywhere("1.1.0")
    checker = make_checker(packages, commands, pypi, npm)
    reports = checker.check()
    assert tuple(report.update_available for report in reports) == (True, True, True)


def test_no_update_when_equal() -> None:
    packages, commands = installed_everywhere("1.0.0")
    pypi, npm = latest_everywhere("1.0.0")
    checker = make_checker(packages, commands, pypi, npm)
    reports = checker.check()
    assert tuple(report.update_available for report in reports) == (False, False, False)


def test_missing_install_has_note() -> None:
    packages, commands = installed_everywhere("1.0.0")
    pypi, npm = latest_everywhere("1.1.0")
    del commands[("opencode", "--version")]
    checker = make_checker(packages, commands, pypi, npm)
    by_name = {report.name: report for report in checker.check()}
    assert by_name["opencode"].note == "not installed"


def test_missing_latest_has_note() -> None:
    packages, commands = installed_everywhere("1.0.0")
    pypi, npm = latest_everywhere("1.1.0")
    del pypi["claude-agent-sdk"]
    checker = make_checker(packages, commands, pypi, npm)
    by_name = {report.name: report for report in checker.check()}
    assert by_name["claude-agent-sdk"].note == "could not read the latest version"


def test_reports_come_in_fixed_order() -> None:
    packages, commands = installed_everywhere("1.0.0")
    pypi, npm = latest_everywhere("1.0.0")
    checker = make_checker(packages, commands, pypi, npm)
    assert [report.name for report in checker.check()] == [
        "claude-agent-sdk",
        "claude-code",
        "opencode",
    ]
