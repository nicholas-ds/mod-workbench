"""Fetch the latest package versions from public registries."""

from __future__ import annotations

import json
from collections.abc import Callable
from urllib.request import Request, urlopen

USER_AGENT = "mod-workbench-version-check"


class LatestVersionFetcher:
    """Read the latest version of a package from PyPI or npm."""

    def __init__(self, fetch_json: Callable[[str], dict]) -> None:
        self._fetch_json = fetch_json

    def pypi(self, package: str) -> str:
        return self._version_for(f"https://pypi.org/pypi/{package}/json", ("info", "version"))

    def npm(self, package: str) -> str:
        escaped = package.replace("/", "%2F")
        return self._version_for(f"https://registry.npmjs.org/{escaped}/latest", ("version",))

    def _version_for(self, url: str, keys: tuple[str, ...]) -> str:
        try:
            payload = self._fetch_json(url)
            for key in keys:
                payload = payload[key]
        except Exception:
            return ""
        return str(payload)


def fetch_json(url: str) -> dict:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=10) as response:
        return json.load(response)
