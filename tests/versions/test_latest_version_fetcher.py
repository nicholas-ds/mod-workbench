"""Tests for fetching latest package versions."""

from workbench.versions.latest_version_fetcher import LatestVersionFetcher


class FakeJson:
    def __init__(self, payload: dict, error: Exception | None = None) -> None:
        self._payload = payload
        self._error = error
        self.urls: list[str] = []

    def fetch(self, url: str) -> dict:
        self.urls.append(url)
        if self._error is not None:
            raise self._error
        return self._payload


def make_fetcher(payload: dict, error: Exception | None = None) -> LatestVersionFetcher:
    return LatestVersionFetcher(FakeJson(payload, error).fetch)


def test_pypi_reads_info_version() -> None:
    fetcher = make_fetcher({"info": {"version": "2.0.1"}})
    assert fetcher.pypi("requests") == "2.0.1"


def test_npm_reads_version() -> None:
    fetcher = make_fetcher({"version": "3.4.0"})
    assert fetcher.npm("typescript") == "3.4.0"


def test_scoped_npm_name_is_escaped() -> None:
    fake = FakeJson({"version": "1.0.0"})
    fetcher = LatestVersionFetcher(fake.fetch)
    assert fetcher.npm("@anthropic-ai/claude-code") == "1.0.0"
    assert fake.urls == ["https://registry.npmjs.org/@anthropic-ai%2Fclaude-code/latest"]


def test_fetch_error_gives_empty_string() -> None:
    fetcher = make_fetcher({}, RuntimeError("fetch failed"))
    assert fetcher.pypi("requests") == ""
    assert fetcher.npm("typescript") == ""
