"""Tests for reading installed package versions."""

from workbench.versions.installed_version_reader import InstalledVersionReader, run_process


class FakeCommands:
    def __init__(self, output: str, error: Exception | None = None) -> None:
        self._output = output
        self._error = error

    def run(self, args: tuple[str, ...]) -> str:
        if self._error is not None:
            raise self._error
        return self._output


def make_reader(output: str, error: Exception | None = None) -> InstalledVersionReader:
    return InstalledVersionReader(FakeCommands(output, error).run)


def test_command_picks_dotted_version_from_output() -> None:
    reader = make_reader("foo 1.2.3 (stable)")
    assert reader.command(("foo", "--version")) == "1.2.3"


def test_command_failure_gives_empty_string() -> None:
    reader = make_reader("", RuntimeError("command failed"))
    assert reader.command(("broken", "--version")) == ""


def test_command_without_version_gives_empty_string() -> None:
    reader = make_reader("no version in this output")
    assert reader.command(("foo", "--version")) == ""


def test_missing_package_gives_empty_string() -> None:
    reader = make_reader("")
    assert reader.package("workbench-definitely-not-installed") == ""


def test_run_process_runs_a_real_program_by_name() -> None:
    import sys
    assert "Python" in run_process((sys.executable, "--version"))


def test_run_process_missing_program_gives_empty_string() -> None:
    assert run_process(("no-such-program-xyz", "--version")) == ""
